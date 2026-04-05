"""
AsyncIndexingPipeline — 7-stage parallel indexing pipeline.

Stage 1: Discovery    — walk repo, file manifest to SQL immediately
Stage 2: Parse        — ProcessPoolExecutor (CPU-bound tree-sitter)
Stage 3: Graph Build  — async, as ParseResults stream in
Stage 4: Git Analysis — runs CONCURRENTLY with Stage 3 (independent)
Stage 5: Embedding    — ThreadPoolExecutor + semaphore
Stage 6: RAG Doc Gen  — asyncio.Semaphore(concurrency), fetches dep docs first
Stage 7: Atomic Commit — per-file coordinator.transaction()

Performance vs repowise: Stages 3+4 run concurrently. Stages 2+5+6 are parallel.
Target: <5 min for 1,000-file repos (vs repowise's 25+ min).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import anthropic
from openai import AsyncOpenAI

from .coordinator import AtomicStorageCoordinator
from ..config import RepomindConfig
from ..generation.cost_tracker import TokenspyCostTracker
from ..generation.generator import RAGAwareDocGenerator
from ..git.cochange import CoChangeAnalyzer
from ..git.history import GitHistoryAnalyzer
from ..git.metrics import TemporalMetricsCalculator
from ..graph.analyzer import GraphAnalyzer
from ..graph.builder import CodeGraphBuilder
from ..parsing import AsyncTreeSitterParser, HintRegistry
from ..storage.graph import GraphStore
from ..storage.sql import AsyncSQLiteDB, FileRepository, GitMetricsRepository
from ..storage.vector import AsyncEmbedder, LanceDBStore
from ..utils.file_utils import detect_language, walk_repo
from ..utils.hash_utils import content_hash, repo_id
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class IndexingProgress:
    stage: str
    current: int
    total: int
    cost_so_far: float = 0.0

    @property
    def pct(self) -> float:
        return (self.current / max(1, self.total)) * 100


ProgressCallback = Callable[[IndexingProgress], None]


class AsyncIndexingPipeline:
    def __init__(self, config: RepomindConfig) -> None:
        self._config = config
        self._repo_id = repo_id(config.repo_path)
        config.ensure_data_dir()

        # Storage
        self._db = AsyncSQLiteDB(config.db_path)
        self._vector = LanceDBStore(config.vector_dir)
        self._graph_store = GraphStore(config.graph_path)
        self._coordinator = AtomicStorageCoordinator(self._db, self._vector, self._graph_store)

        # Repos
        self._file_repo = FileRepository(self._db)
        self._metrics_repo = GitMetricsRepository(self._db)

        self._progress_cb: ProgressCallback | None = None

    def on_progress(self, cb: ProgressCallback) -> None:
        self._progress_cb = cb

    def _emit(self, stage: str, current: int, total: int, cost: float = 0.0) -> None:
        if self._progress_cb:
            self._progress_cb(IndexingProgress(stage, current, total, cost))

    async def run(self, incremental: bool = True) -> None:
        await self._db.connect()
        await self._vector.connect()
        self._graph_store.load()

        # Set up LLM clients
        anthropic_client = anthropic.AsyncAnthropic(api_key=self._config.anthropic_api_key or None)
        openai_client = AsyncOpenAI(api_key=self._config.openai_api_key or None)
        embedder = AsyncEmbedder(
            model=self._config.llm.embedding_model,
            client=openai_client,
            concurrency=self._config.llm.embedding_concurrency,
        )
        cost_tracker = TokenspyCostTracker(self._db, self._repo_id)
        graph_builder = CodeGraphBuilder(self._graph_store, self._config.repo_path)

        try:
            # Stage 1: Discovery
            files = await self._stage1_discovery(incremental)
            if not files:
                log.info("nothing_to_index")
                return

            # Stage 2: Parse (CPU-bound, ProcessPoolExecutor)
            parse_results = await self._stage2_parse(files)

            # Stage 3 + 4: Graph Build + Git Analysis (concurrent)
            hints = HintRegistry()
            dynamic_edges = await asyncio.get_event_loop().run_in_executor(
                None, hints.extract_all, self._config.repo_path
            )
            git_metrics_map = {}

            await asyncio.gather(
                self._stage3_graph_build(parse_results, graph_builder, dynamic_edges),
                self._stage4_git_analysis(files, git_metrics_map),
            )

            # Compute graph metrics (PageRank, communities) AFTER graph is built
            await self._compute_graph_metrics(graph_builder)

            # Stage 5 + 6: Embed + Generate (concurrent per file)
            gen_sem = asyncio.Semaphore(self._config.llm.generation_concurrency)
            doc_generator = RAGAwareDocGenerator(
                client=anthropic_client,
                model=self._config.llm.model,
                embedder=embedder,
                vector_store=self._vector,
                graph_builder=graph_builder,
                cost_tracker=cost_tracker,
                repo_id=self._repo_id,
                max_tokens=self._config.llm.max_tokens,
            )

            total = len(parse_results)
            done = [0]

            async def _process_file(pr, content: str) -> None:
                async with gen_sem:
                    centrality = float(
                        self._graph_store.get_node_attrs(pr.file_path).get("centrality", 0.0)
                    )
                    metrics = git_metrics_map.get(pr.file_path)
                    hotspot = float(metrics.temporal_hotspot_score) if metrics else 0.0

                    try:
                        doc = await doc_generator.generate(
                            pr, content, centrality=centrality, hotspot_score=hotspot
                        )
                        async with self._coordinator.transaction() as txn:
                            txn.pending_vector_records.append(doc.vector_record)
                            txn.pending_vector_ids.append(doc.vector_record["id"])
                    except Exception as e:
                        log.warning("file_processing_failed", file=pr.file_path, error=str(e))

                    done[0] += 1
                    self._emit(
                        "Generating Docs",
                        done[0],
                        total,
                        cost_tracker.session_cost,
                    )

            # Load file contents (needed for generation)
            content_map: dict[str, str] = {}
            for pr in parse_results:
                try:
                    content_map[pr.file_path] = Path(pr.file_path).read_text(errors="replace")
                except Exception:
                    content_map[pr.file_path] = ""

            tasks = [_process_file(pr, content_map[pr.file_path]) for pr in parse_results]
            await asyncio.gather(*tasks)

            # Stage 7: Save git metrics to SQL + graph to disk
            await self._stage7_persist_metrics(files, git_metrics_map)
            await self._coordinator.save_graph()

            log.info(
                "indexing_complete",
                files=len(files),
                cost_usd=cost_tracker.session_cost,
                tokens=cost_tracker.session_tokens,
            )

        finally:
            await self._db.close()

    async def _stage1_discovery(self, incremental: bool) -> list[Path]:
        self._emit("Discovering Files", 0, 1)
        cfg = self._config.indexing
        all_files = walk_repo(
            self._config.repo_path,
            cfg.exclude_patterns,
            cfg.languages,
            cfg.max_file_size_bytes,
        )

        if incremental:
            to_index: list[Path] = []
            for fp in all_files:
                lang = detect_language(fp)
                if not lang:
                    continue
                current_hash = content_hash(fp)
                stored_hash = await self._file_repo.get_content_hash(
                    self._repo_id, str(fp)
                )
                if stored_hash != current_hash:
                    to_index.append(fp)
            log.info("discovery_incremental", total=len(all_files), to_index=len(to_index))
            self._emit("Discovering Files", len(to_index), len(to_index))
            return to_index

        self._emit("Discovering Files", len(all_files), len(all_files))
        return all_files

    async def _stage2_parse(self, files: list[Path]) -> list:
        from ..parsing.symbols import ParseResult
        self._emit("Parsing", 0, len(files))
        parser = AsyncTreeSitterParser(workers=self._config.indexing.worker_processes)
        parser.start()

        pairs = []
        for fp in files:
            lang = detect_language(fp)
            if lang:
                pairs.append((fp, lang))

        results = await parser.parse_batch(pairs, concurrency=self._config.indexing.worker_processes * 4)
        parser.stop()

        # Register files in SQL
        for fp, pr in zip(files, results):
            lang = detect_language(fp) or "unknown"
            try:
                size = fp.stat().st_size
                c_hash = content_hash(fp)
                file_id = await self._file_repo.upsert(
                    self._repo_id, str(fp), lang, size, c_hash
                )
                # Insert symbols
                for sym in pr.symbols:
                    await self._file_repo.insert_symbol(
                        file_id, sym.name, sym.kind,
                        sym.line_start, sym.line_end,
                        sym.visibility, sym.signature,
                    )
                # Insert imports
                for imp in pr.imports:
                    await self._file_repo.insert_import(
                        file_id, imp.source,
                        ",".join(imp.names) if imp.names else None,
                        imp.is_dynamic, imp.hint_source,
                    )
            except Exception as e:
                log.warning("sql_insert_failed", file=str(fp), error=str(e))

        self._emit("Parsing", len(results), len(results))
        return [r for r in results if r.is_valid]

    async def _stage3_graph_build(self, parse_results: list, builder: CodeGraphBuilder, dynamic_edges) -> None:
        self._emit("Building Graph", 0, len(parse_results))
        for pr in parse_results:
            builder.add_file(pr)
        for pr in parse_results:
            builder.add_imports(pr)
        builder.add_dynamic_edges(dynamic_edges)
        self._emit("Building Graph", len(parse_results), len(parse_results))

    async def _stage4_git_analysis(self, files: list[Path], metrics_out: dict) -> None:
        self._emit("Analyzing Git", 0, 1)
        git = GitHistoryAnalyzer(
            self._config.repo_path,
            max_commits=self._config.git.max_commits,
        )
        if not git.open():
            return

        calculator = TemporalMetricsCalculator(
            halflife_days=self._config.git.decay_halflife_days,
        )
        cochange = CoChangeAnalyzer(
            halflife_days=self._config.git.decay_halflife_days,
            window_days=self._config.git.cochange_window_days,
        )

        # Analyze all commits for co-change detection
        all_commits = await asyncio.get_event_loop().run_in_executor(
            None, git.get_recent_commits
        )
        cochange_pairs = cochange.analyze(all_commits)

        # Per-file metrics
        for fp in files:
            history = await asyncio.get_event_loop().run_in_executor(
                None, git.get_file_history, str(fp)
            )
            m = calculator.compute(history)
            metrics_out[str(fp)] = m

        # Store co-change pairs
        for pair in cochange_pairs[:500]:  # top 500 pairs
            fa_rec = await self._file_repo.get_by_path(self._repo_id, pair.file_a)
            fb_rec = await self._file_repo.get_by_path(self._repo_id, pair.file_b)
            if fa_rec and fb_rec:
                await self._metrics_repo.upsert_cochange(
                    self._repo_id,
                    fa_rec["id"],
                    fb_rec["id"],
                    pair.cochange_count,
                    pair.cochange_score,
                )

        git.close()
        self._emit("Analyzing Git", 1, 1)

    async def _compute_graph_metrics(self, builder: CodeGraphBuilder) -> None:
        self._emit("Computing Graph Metrics", 0, 1)
        analyzer = GraphAnalyzer(self._graph_store)
        loop = asyncio.get_event_loop()
        pagerank = await loop.run_in_executor(None, analyzer.compute_pagerank)
        communities = await loop.run_in_executor(None, analyzer.compute_communities)
        for node_id, centrality in pagerank.items():
            builder.update_node_metrics(
                node_id,
                centrality=centrality,
                community_id=communities.get(node_id, -1),
                hotspot_score=0.0,  # updated in stage 7
            )
        self._emit("Computing Graph Metrics", 1, 1)

    async def _stage7_persist_metrics(self, files: list[Path], metrics_map: dict) -> None:
        self._emit("Persisting Metrics", 0, len(files))
        for i, fp in enumerate(files):
            m = metrics_map.get(str(fp))
            if m:
                file_rec = await self._file_repo.get_by_path(self._repo_id, str(fp))
                if file_rec:
                    await self._metrics_repo.upsert(
                        file_id=file_rec["id"],
                        hotspot_score=m.hotspot_score,
                        temporal_hotspot_score=m.temporal_hotspot_score,
                        owner_email=m.owner_email,
                        ownership_pct=m.ownership_pct,
                        churn_count=m.churn_count,
                    )
            self._emit("Persisting Metrics", i + 1, len(files))
