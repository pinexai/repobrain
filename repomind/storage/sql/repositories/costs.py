from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..database import AsyncSQLiteDB


class CostRepository:
    def __init__(self, db: AsyncSQLiteDB) -> None:
        self._db = db

    async def record(
        self,
        repo_id: str,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        file_path: str | None = None,
    ) -> None:
        await self._db.execute(
            """INSERT INTO llm_costs (id, repo_id, file_path, operation, model,
               input_tokens, output_tokens, cost_usd, called_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), repo_id, file_path, operation, model,
             input_tokens, output_tokens, cost_usd, _now()),
        )
        await self._db._conn.commit()  # type: ignore[union-attr]

    async def get_summary(self, repo_id: str, since: str | None = None) -> dict:
        where = "WHERE repo_id = ?"
        params: tuple = (repo_id,)
        if since:
            where += " AND called_at >= ?"
            params = (repo_id, since)

        row = await self._db.fetchone(
            f"""SELECT COUNT(*) as calls,
                       SUM(input_tokens + output_tokens) as total_tokens,
                       SUM(cost_usd) as total_cost
                FROM llm_costs {where}""",
            params,
        )
        return dict(row) if row else {"calls": 0, "total_tokens": 0, "total_cost": 0.0}

    async def get_by_operation(self, repo_id: str) -> list[dict]:
        rows = await self._db.fetchall(
            """SELECT operation,
                      COUNT(*) as calls,
                      SUM(input_tokens + output_tokens) as total_tokens,
                      SUM(cost_usd) as total_cost
               FROM llm_costs WHERE repo_id = ?
               GROUP BY operation
               ORDER BY total_cost DESC""",
            (repo_id,),
        )
        return [dict(r) for r in rows]

    async def get_by_model(self, repo_id: str) -> list[dict]:
        rows = await self._db.fetchall(
            """SELECT model,
                      COUNT(*) as calls,
                      SUM(cost_usd) as total_cost
               FROM llm_costs WHERE repo_id = ?
               GROUP BY model ORDER BY total_cost DESC""",
            (repo_id,),
        )
        return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
