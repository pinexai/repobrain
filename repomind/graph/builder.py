from __future__ import annotations

from pathlib import Path

from ..parsing.symbols import ParseResult
from ..parsing.dynamic_hints import DynamicEdge
from ..storage.graph import GraphStore
from ..utils.logging import get_logger

log = get_logger(__name__)


class CodeGraphBuilder:
    """Builds the dependency graph from ParseResults + dynamic hints."""

    def __init__(self, graph_store: GraphStore, repo_root: Path) -> None:
        self._store = graph_store
        self._root = repo_root

    def add_file(
        self,
        parse_result: ParseResult,
        centrality: float = 0.0,
        community_id: int = -1,
        hotspot_score: float = 0.0,
    ) -> None:
        """Add a file node. Called once per parsed file."""
        self._store.add_node(
            parse_result.file_path,
            type="file",
            language=parse_result.language,
            centrality=centrality,
            community_id=community_id,
            hotspot_score=hotspot_score,
            symbol_count=len(parse_result.symbols),
        )

    def add_imports(self, parse_result: ParseResult) -> None:
        """Add import edges from a parse result."""
        for imp in parse_result.imports:
            resolved = self._resolve_import(parse_result.file_path, imp.source)
            if resolved and resolved != parse_result.file_path:
                edge_type = "dynamic_uses" if imp.is_dynamic else "imports"
                hint = imp.hint_source or ""
                self._store.add_edge(
                    parse_result.file_path,
                    resolved,
                    type=edge_type,
                    hint_source=hint,
                    weight=1.0,
                )

    def add_dynamic_edges(self, edges: list[DynamicEdge]) -> None:
        """Add hint-derived edges (Django, pytest, Node)."""
        for edge in edges:
            if self._store.has_node(edge.source) and self._store.has_node(edge.target):
                self._store.add_edge(
                    edge.source,
                    edge.target,
                    type=edge.edge_type,
                    hint_source=edge.hint_source,
                    weight=edge.weight,
                )

    def update_node_metrics(
        self,
        file_path: str,
        centrality: float,
        community_id: int,
        hotspot_score: float,
    ) -> None:
        node = self._store.get_node_attrs(file_path)
        if node:
            self._store.add_node(
                file_path,
                **{**node, "centrality": centrality, "community_id": community_id, "hotspot_score": hotspot_score},
            )

    def _resolve_import(self, source_file: str, import_str: str) -> str | None:
        """Resolve import string to absolute file path."""
        if not import_str:
            return None

        source_path = Path(source_file)

        # Relative imports (./foo, ../bar)
        if import_str.startswith("."):
            from ..utils.file_utils import relative_import_to_path
            resolved = relative_import_to_path(source_path, import_str, self._root)
            return str(resolved) if resolved else None

        # Absolute module path (e.g. "myapp.utils.helpers")
        parts = import_str.replace(".", "/").split("/")
        for attempt in [
            self._root / Path(*parts),
            self._root / Path(*parts[1:]) if len(parts) > 1 else None,
        ]:
            if attempt is None:
                continue
            for suffix in [".py", ".ts", ".js", "/__init__.py", "/index.ts", "/index.js"]:
                candidate = Path(str(attempt) + suffix)
                if candidate.exists():
                    return str(candidate)

        return None

    def get_direct_dependencies(self, file_path: str) -> list[str]:
        return self._store.successors(file_path)

    def get_reverse_dependencies(self, file_path: str) -> list[str]:
        return self._store.predecessors(file_path)
