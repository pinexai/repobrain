from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa


def _make_schemas(dim: int) -> tuple[pa.Schema, pa.Schema, pa.Schema]:
    file_docs = pa.schema([
        pa.field("id", pa.string()),
        pa.field("repo_id", pa.string()),
        pa.field("file_path", pa.string()),
        pa.field("language", pa.string()),
        pa.field("doc_summary", pa.string()),
        pa.field("key_exports", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), dim)),
        pa.field("indexed_at", pa.string()),
    ])
    symbol_docs = pa.schema([
        pa.field("id", pa.string()),
        pa.field("file_path", pa.string()),
        pa.field("name", pa.string()),
        pa.field("kind", pa.string()),
        pa.field("doc_text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), dim)),
    ])
    code_chunks = pa.schema([
        pa.field("id", pa.string()),
        pa.field("file_path", pa.string()),
        pa.field("chunk_index", pa.int32()),
        pa.field("content", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), dim)),
    ])
    return file_docs, symbol_docs, code_chunks


class LanceDBStore:
    def __init__(self, vector_dir: Path, vector_dim: int = 1536) -> None:
        self._dir = vector_dir
        self._vector_dim = vector_dim
        self._db: Any = None
        self._file_docs: Any = None
        self._symbol_docs: Any = None
        self._code_chunks: Any = None

    async def connect(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        self._db = await loop.run_in_executor(None, lancedb.connect, str(self._dir))
        _file_schema, _sym_schema, _chunk_schema = _make_schemas(self._vector_dim)
        self._file_docs = await self._get_or_create("file_docs", _file_schema)
        self._symbol_docs = await self._get_or_create("symbol_docs", _sym_schema)
        self._code_chunks = await self._get_or_create("code_chunks", _chunk_schema)

    async def _get_or_create(self, name: str, schema: pa.Schema) -> Any:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._db.open_table, name)
        except Exception:
            empty = pa.table({f.name: pa.array([], type=f.type) for f in schema})
            return await loop.run_in_executor(
                None, lambda: self._db.create_table(name, data=empty, schema=schema)
            )

    async def upsert_file_doc(self, record: dict) -> None:
        loop = asyncio.get_running_loop()
        # Delete existing first
        await loop.run_in_executor(
            None,
            lambda: self._file_docs.delete(
                f"id = '{record['id']}'"
            ) if self._file_docs else None,
        )
        table = pa.table({k: [v] for k, v in record.items()})
        await loop.run_in_executor(None, self._file_docs.add, table)

    async def upsert_symbol_doc(self, record: dict) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._symbol_docs.delete(f"id = '{record['id']}'"),
        )
        table = pa.table({k: [v] for k, v in record.items()})
        await loop.run_in_executor(None, self._symbol_docs.add, table)

    async def upsert_code_chunk(self, record: dict) -> None:
        loop = asyncio.get_running_loop()
        table = pa.table({k: [v] for k, v in record.items()})
        await loop.run_in_executor(None, self._code_chunks.add, table)

    async def search_file_docs(
        self,
        vector: list[float],
        repo_id: str,
        top_k: int = 10,
        language: str | None = None,
    ) -> list[dict]:
        loop = asyncio.get_running_loop()

        def _search() -> list[dict]:
            q = self._file_docs.search(vector).limit(top_k * 2)
            results = q.to_list()
            filtered = [r for r in results if r.get("repo_id") == repo_id]
            if language:
                filtered = [r for r in filtered if r.get("language") == language]
            return filtered[:top_k]

        return await loop.run_in_executor(None, _search)

    async def search_code_chunks(
        self,
        vector: list[float],
        top_k: int = 10,
    ) -> list[dict]:
        loop = asyncio.get_running_loop()

        def _search() -> list[dict]:
            return self._code_chunks.search(vector).limit(top_k).to_list()

        return await loop.run_in_executor(None, _search)

    async def get_file_doc_by_path(self, file_path: str) -> dict | None:
        loop = asyncio.get_running_loop()

        def _get() -> dict | None:
            results = (
                self._file_docs.search()
                .where(f"file_path = '{file_path}'")
                .limit(1)
                .to_list()
            )
            return results[0] if results else None

        return await loop.run_in_executor(None, _get)

    async def delete_by_file_path(self, file_path: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._file_docs.delete(f"file_path = '{file_path}'"),
        )
        await loop.run_in_executor(
            None,
            lambda: self._symbol_docs.delete(f"file_path = '{file_path}'"),
        )
        await loop.run_in_executor(
            None,
            lambda: self._code_chunks.delete(f"file_path = '{file_path}'"),
        )

    async def delete_pending_ids(self, ids: list[str]) -> None:
        """Roll back buffered inserts by ID."""
        loop = asyncio.get_running_loop()
        for doc_id in ids:
            id_str = f"id = '{doc_id}'"
            await loop.run_in_executor(None, lambda: self._file_docs.delete(id_str))
            await loop.run_in_executor(None, lambda: self._symbol_docs.delete(id_str))
            await loop.run_in_executor(None, lambda: self._code_chunks.delete(id_str))
