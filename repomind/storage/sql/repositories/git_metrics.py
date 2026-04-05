from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..database import AsyncSQLiteDB


class GitMetricsRepository:
    def __init__(self, db: AsyncSQLiteDB) -> None:
        self._db = db

    async def upsert(
        self,
        file_id: str,
        hotspot_score: float,
        temporal_hotspot_score: float,
        owner_email: str,
        ownership_pct: float,
        churn_count: int,
    ) -> None:
        existing = await self._db.fetchone(
            "SELECT id FROM file_git_metrics WHERE file_id = ?", (file_id,)
        )
        if existing:
            await self._db.execute(
                """UPDATE file_git_metrics
                   SET hotspot_score=?, temporal_hotspot_score=?, owner_email=?,
                       ownership_pct=?, churn_count=?, last_computed_at=?
                   WHERE file_id=?""",
                (hotspot_score, temporal_hotspot_score, owner_email,
                 ownership_pct, churn_count, _now(), file_id),
            )
        else:
            await self._db.execute(
                """INSERT INTO file_git_metrics
                   (id, file_id, hotspot_score, temporal_hotspot_score, owner_email,
                    ownership_pct, churn_count, last_computed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), file_id, hotspot_score, temporal_hotspot_score,
                 owner_email, ownership_pct, churn_count, _now()),
            )
        await self._db._conn.commit()  # type: ignore[union-attr]
        # CRITICAL: always refresh percentile ranks globally after any metric write
        await self.refresh_percentile_ranks()

    async def refresh_percentile_ranks(self) -> None:
        """
        Recompute percentile ranks globally using window function.
        This is what repowise MISSES in incremental updates.
        """
        await self._db.execute("""
            UPDATE file_git_metrics
            SET percentile_rank = ranked.prank
            FROM (
                SELECT id,
                       PERCENT_RANK() OVER (ORDER BY temporal_hotspot_score) AS prank
                FROM file_git_metrics
            ) AS ranked
            WHERE file_git_metrics.id = ranked.id
        """)
        await self._db._conn.commit()  # type: ignore[union-attr]

    async def get_by_file(self, file_id: str) -> dict | None:
        row = await self._db.fetchone(
            "SELECT * FROM file_git_metrics WHERE file_id = ?", (file_id,)
        )
        return dict(row) if row else None

    async def get_hotspots(
        self,
        repo_id: str,
        top_n: int = 20,
        language: str | None = None,
    ) -> list[dict]:
        lang_filter = "AND f.language = ?" if language else ""
        params: tuple = (repo_id, top_n) if not language else (repo_id, language, top_n)
        rows = await self._db.fetchall(
            f"""SELECT m.*, f.path, f.language FROM file_git_metrics m
               JOIN files f ON m.file_id = f.id
               WHERE f.repo_id = ? {lang_filter}
               ORDER BY m.temporal_hotspot_score DESC
               LIMIT ?""",
            params,
        )
        return [dict(r) for r in rows]

    async def upsert_cochange(
        self,
        repo_id: str,
        file_id_a: str,
        file_id_b: str,
        cochange_count: int,
        cochange_score: float,
    ) -> None:
        existing = await self._db.fetchone(
            "SELECT id FROM cochange_pairs WHERE repo_id=? AND file_id_a=? AND file_id_b=?",
            (repo_id, file_id_a, file_id_b),
        )
        if existing:
            await self._db.execute(
                """UPDATE cochange_pairs SET cochange_count=?, cochange_score=?
                   WHERE repo_id=? AND file_id_a=? AND file_id_b=?""",
                (cochange_count, cochange_score, repo_id, file_id_a, file_id_b),
            )
        else:
            await self._db.execute(
                """INSERT INTO cochange_pairs (id, repo_id, file_id_a, file_id_b, cochange_count, cochange_score)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), repo_id, file_id_a, file_id_b, cochange_count, cochange_score),
            )
        await self._db._conn.commit()  # type: ignore[union-attr]

    async def get_cochange_partners(
        self,
        file_id: str,
        repo_id: str,
        min_score: float = 0.3,
    ) -> list[dict]:
        rows = await self._db.fetchall(
            """SELECT cp.*, f.path as partner_path FROM cochange_pairs cp
               JOIN files f ON (
                 CASE WHEN cp.file_id_a = ? THEN cp.file_id_b ELSE cp.file_id_a END = f.id
               )
               WHERE (cp.file_id_a = ? OR cp.file_id_b = ?)
                 AND cp.repo_id = ?
                 AND cp.cochange_score >= ?
               ORDER BY cp.cochange_score DESC""",
            (file_id, file_id, file_id, repo_id, min_score),
        )
        return [dict(r) for r in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
