from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..database import AsyncSQLiteDB


class FileRepository:
    def __init__(self, db: AsyncSQLiteDB) -> None:
        self._db = db

    async def upsert(
        self,
        repo_id: str,
        path: str,
        language: str,
        size_bytes: int,
        content_hash: str,
    ) -> str:
        existing = await self._db.fetchone(
            "SELECT id FROM files WHERE repo_id = ? AND path = ?",
            (repo_id, path),
        )
        if existing:
            file_id = existing["id"]
            await self._db.execute(
                """UPDATE files SET language=?, size_bytes=?, content_hash=?, indexed_at=?
                   WHERE id=?""",
                (language, size_bytes, content_hash, _now(), file_id),
            )
            await self._db.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            await self._db.execute("DELETE FROM imports WHERE file_id = ?", (file_id,))
        else:
            file_id = str(uuid.uuid4())
            await self._db.execute(
                """INSERT INTO files (id, repo_id, path, language, size_bytes, content_hash, indexed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (file_id, repo_id, path, language, size_bytes, content_hash, _now()),
            )
        await self._db._conn.commit()  # type: ignore[union-attr]
        return file_id

    async def get_by_path(self, repo_id: str, path: str) -> dict | None:
        row = await self._db.fetchone(
            "SELECT * FROM files WHERE repo_id = ? AND path = ?",
            (repo_id, path),
        )
        return dict(row) if row else None

    async def get_all(self, repo_id: str) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT * FROM files WHERE repo_id = ?", (repo_id,)
        )
        return [dict(r) for r in rows]

    async def get_content_hash(self, repo_id: str, path: str) -> str | None:
        row = await self._db.fetchone(
            "SELECT content_hash FROM files WHERE repo_id = ? AND path = ?",
            (repo_id, path),
        )
        return row["content_hash"] if row else None

    async def mark_doc_generated(self, file_id: str) -> None:
        await self._db.execute(
            "UPDATE files SET doc_generated_at = ? WHERE id = ?",
            (_now(), file_id),
        )
        await self._db._conn.commit()  # type: ignore[union-attr]

    async def insert_symbol(
        self,
        file_id: str,
        name: str,
        kind: str,
        line_start: int,
        line_end: int,
        visibility: str = "public",
        signature: str | None = None,
    ) -> str:
        sym_id = str(uuid.uuid4())
        await self._db.execute(
            """INSERT INTO symbols (id, file_id, name, kind, line_start, line_end, visibility, signature)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (sym_id, file_id, name, kind, line_start, line_end, visibility, signature),
        )
        return sym_id

    async def insert_import(
        self,
        file_id: str,
        source_path: str,
        imported_names: str | None,
        is_dynamic: bool = False,
        hint_source: str | None = None,
    ) -> str:
        imp_id = str(uuid.uuid4())
        await self._db.execute(
            """INSERT INTO imports (id, file_id, source_path, imported_names, is_dynamic, hint_source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (imp_id, file_id, source_path, imported_names, int(is_dynamic), hint_source),
        )
        return imp_id

    async def get_imports(self, file_id: str) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT * FROM imports WHERE file_id = ?", (file_id,)
        )
        return [dict(r) for r in rows]

    async def get_symbols(self, file_id: str) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT * FROM symbols WHERE file_id = ?", (file_id,)
        )
        return [dict(r) for r in rows]

    async def search_symbols(self, repo_id: str, name: str) -> list[dict]:
        rows = await self._db.fetchall(
            """SELECT s.*, f.path as file_path FROM symbols s
               JOIN files f ON s.file_id = f.id
               WHERE f.repo_id = ? AND s.name LIKE ?""",
            (repo_id, f"%{name}%"),
        )
        return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
