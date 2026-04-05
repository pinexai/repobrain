"""
RAGAwareDocGenerator — fixes repowise's #1 architectural flaw.

Before generating documentation for any file:
1. Fetch the file's direct dependencies from the graph
2. Retrieve existing docs for those dependencies from LanceDB
3. Include those docs as context in the generation prompt

This ensures generated docs accurately describe how a module uses its dependencies,
instead of guessing or hallucinating.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import anthropic

from .cost_tracker import TokenspyCostTracker
from .prompts import PromptTemplates
from .rag import DependencyContextRetriever
from ..graph.builder import CodeGraphBuilder
from ..parsing.symbols import ParseResult
from ..storage.vector import AsyncEmbedder, LanceDBStore
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class GeneratedDoc:
    file_path: str
    doc_text: str
    summary: str       # first 500 chars of doc_text
    key_exports: str   # comma-separated export names
    vector_record: dict


class RAGAwareDocGenerator:
    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        embedder: AsyncEmbedder,
        vector_store: LanceDBStore,
        graph_builder: CodeGraphBuilder,
        cost_tracker: TokenspyCostTracker,
        repo_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> None:
        self._client = client
        self._model = model
        self._embedder = embedder
        self._vector_store = vector_store
        self._graph_builder = graph_builder
        self._cost_tracker = cost_tracker
        self._repo_id = repo_id
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._rag = DependencyContextRetriever(vector_store)

    async def generate(
        self,
        parse_result: ParseResult,
        file_content: str,
        centrality: float = 0.0,
        hotspot_score: float = 0.0,
    ) -> GeneratedDoc:
        file_path = parse_result.file_path

        # ── Step 1: Get direct dependencies ──────────────────────────────────
        dep_paths = self._graph_builder.get_direct_dependencies(file_path)

        # ── Step 2: Retrieve dependency docs from vector store BEFORE generating ──
        # THIS IS THE FIX — repowise never does this
        dep_contexts = await self._rag.get_docs(dep_paths)
        log.debug(
            "rag_context_loaded",
            file=file_path,
            deps=len(dep_paths),
            context_found=len(dep_contexts),
        )

        # ── Step 3: Build prompt with dependency context ──────────────────────
        symbol_names = [f"{s.kind}:{s.name}" for s in parse_result.symbols]
        prompt = PromptTemplates.doc_generation(
            file_path=file_path,
            file_content=file_content[:6000],
            language=parse_result.language,
            symbols=symbol_names,
            dependency_contexts=dep_contexts,
            centrality=centrality,
            hotspot_score=hotspot_score,
        )

        # ── Step 4: Generate with cost tracking ──────────────────────────────
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            doc_text = response.content[0].text if response.content else ""
            await self._cost_tracker.record(
                model=self._model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                operation="doc_generation",
                file_path=file_path,
            )
        except Exception as e:
            log.warning("doc_generation_failed", file=file_path, error=str(e))
            doc_text = f"# {file_path}\n\n*Documentation generation failed: {e}*"

        # ── Step 5: Embed the generated doc ──────────────────────────────────
        summary = doc_text[:500]
        key_exports = ", ".join(
            s.name for s in parse_result.symbols
            if s.visibility == "public"
        )[:500]

        vector = await self._embedder.embed(doc_text[:4000])
        await self._cost_tracker.record(
            model=self._embedder._model,
            input_tokens=len(doc_text.split()),
            output_tokens=0,
            operation="embedding",
            file_path=file_path,
        )

        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{self._repo_id}:{file_path}"))
        vector_record = {
            "id": doc_id,
            "repo_id": self._repo_id,
            "file_path": file_path,
            "language": parse_result.language,
            "doc_summary": summary,
            "key_exports": key_exports,
            "vector": vector,
            "indexed_at": _now(),
        }

        return GeneratedDoc(
            file_path=file_path,
            doc_text=doc_text,
            summary=summary,
            key_exports=key_exports,
            vector_record=vector_record,
        )


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
