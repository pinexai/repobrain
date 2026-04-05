from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..database import AsyncSQLiteDB


class DecisionRepository:
    def __init__(self, db: AsyncSQLiteDB) -> None:
        self._db = db

    async def create(
        self,
        repo_id: str,
        title: str,
        decision_text: str,
        context_text: str | None = None,
        consequences: str | None = None,
        files_affected: list[str] | None = None,
    ) -> str:
        dec_id = str(uuid.uuid4())
        await self._db.execute(
            """INSERT INTO decisions (id, repo_id, title, context_text, decision_text,
               consequences, files_affected, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (dec_id, repo_id, title, context_text, decision_text,
             ",".join(files_affected or []), _now()),
        )
        await self._db._conn.commit()  # type: ignore[union-attr]
        return dec_id

    async def get_all(self, repo_id: str) -> list[dict]:
        rows = await self._db.fetchall(
            "SELECT * FROM decisions WHERE repo_id = ? ORDER BY created_at DESC",
            (repo_id,),
        )
        return [dict(r) for r in rows]

    async def get_by_file(self, repo_id: str, file_path: str) -> list[dict]:
        rows = await self._db.fetchall(
            """SELECT * FROM decisions
               WHERE repo_id = ? AND files_affected LIKE ?
               ORDER BY created_at DESC""",
            (repo_id, f"%{file_path}%"),
        )
        return [dict(r) for r in rows]

    async def mark_stale(self, dec_id: str) -> None:
        await self._db.execute(
            "UPDATE decisions SET is_stale = 1 WHERE id = ?", (dec_id,)
        )
        await self._db._conn.commit()  # type: ignore[union-attr]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
