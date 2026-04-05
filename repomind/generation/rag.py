"""
DependencyContextRetriever — the fix for repowise's #1 flaw.

Repowise populates a vector store but NEVER queries it during doc generation.
Files generate without knowing what their dependencies actually do.

This retriever fetches actual documentation for a file's dependencies
BEFORE the LLM generates docs for the dependent file.
Result: docs that accurately describe how a module uses its dependencies.
"""
from __future__ import annotations

from ..storage.vector import LanceDBStore
from ..generation.prompts import DepContext
from ..utils.logging import get_logger

log = get_logger(__name__)


class DependencyContextRetriever:
    def __init__(self, vector_store: LanceDBStore) -> None:
        self._store = vector_store

    async def get_docs(self, dep_file_paths: list[str]) -> list[DepContext]:
        """
        Retrieve existing documentation for dependency files.
        Called BEFORE generating docs for the dependent file.
        """
        contexts: list[DepContext] = []
        for path in dep_file_paths:
            try:
                doc = await self._store.get_file_doc_by_path(path)
                if doc:
                    contexts.append(DepContext(
                        file_path=path,
                        summary=doc.get("doc_summary", "")[:1000],
                        key_exports=doc.get("key_exports", ""),
                    ))
            except Exception as e:
                log.debug("dep_context_fetch_failed", path=path, error=str(e))
        return contexts

    async def search_similar(
        self,
        query_vector: list[float],
        repo_id: str,
        top_k: int = 5,
    ) -> list[DepContext]:
        """Semantic search for relevant documentation chunks."""
        results = await self._store.search_file_docs(query_vector, repo_id, top_k)
        return [
            DepContext(
                file_path=r.get("file_path", ""),
                summary=r.get("doc_summary", "")[:500],
                key_exports=r.get("key_exports", ""),
            )
            for r in results
        ]
