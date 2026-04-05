from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite


class AsyncSQLiteDB:
    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self._path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.execute("PRAGMA synchronous=NORMAL")
        await self._migrate()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        assert self._conn, "DB not connected"
        async with self._conn.cursor() as cur:
            try:
                yield self._conn
                await self._conn.commit()
            except Exception:
                await self._conn.rollback()
                raise

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        assert self._conn, "DB not connected"
        return await self._conn.execute(sql, params)

    async def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> None:
        assert self._conn, "DB not connected"
        await self._conn.executemany(sql, params)
        await self._conn.commit()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        assert self._conn, "DB not connected"
        async with self._conn.execute(sql, params) as cur:
            return await cur.fetchall()

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        assert self._conn, "DB not connected"
        async with self._conn.execute(sql, params) as cur:
            return await cur.fetchone()

    async def _migrate(self) -> None:
        assert self._conn
        await self._conn.executescript(_SCHEMA_SQL)
        await self._conn.commit()


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id          TEXT PRIMARY KEY,
    repo_id     TEXT NOT NULL,
    path        TEXT NOT NULL,
    language    TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    indexed_at  TEXT NOT NULL,
    doc_generated_at TEXT,
    UNIQUE(repo_id, path)
);

CREATE TABLE IF NOT EXISTS symbols (
    id          TEXT PRIMARY KEY,
    file_id     TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    kind        TEXT NOT NULL,
    line_start  INTEGER NOT NULL,
    line_end    INTEGER NOT NULL,
    visibility  TEXT NOT NULL DEFAULT 'public',
    signature   TEXT
);

CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);

CREATE TABLE IF NOT EXISTS imports (
    id              TEXT PRIMARY KEY,
    file_id         TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    source_path     TEXT NOT NULL,
    imported_names  TEXT,
    is_dynamic      INTEGER NOT NULL DEFAULT 0,
    hint_source     TEXT
);

CREATE INDEX IF NOT EXISTS idx_imports_file ON imports(file_id);

CREATE TABLE IF NOT EXISTS git_commits (
    id              TEXT PRIMARY KEY,
    repo_id         TEXT NOT NULL,
    sha             TEXT NOT NULL,
    author_email    TEXT NOT NULL,
    authored_at     TEXT NOT NULL,
    message_summary TEXT,
    files_changed   TEXT,
    UNIQUE(repo_id, sha)
);

CREATE TABLE IF NOT EXISTS file_git_metrics (
    id                      TEXT PRIMARY KEY,
    file_id                 TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    hotspot_score           REAL NOT NULL DEFAULT 0,
    temporal_hotspot_score  REAL NOT NULL DEFAULT 0,
    percentile_rank         REAL NOT NULL DEFAULT 0,
    owner_email             TEXT NOT NULL DEFAULT '',
    ownership_pct           REAL NOT NULL DEFAULT 0,
    churn_count             INTEGER NOT NULL DEFAULT 0,
    last_computed_at        TEXT NOT NULL,
    UNIQUE(file_id)
);

CREATE INDEX IF NOT EXISTS idx_git_metrics_percentile ON file_git_metrics(percentile_rank DESC);

CREATE TABLE IF NOT EXISTS cochange_pairs (
    id              TEXT PRIMARY KEY,
    repo_id         TEXT NOT NULL,
    file_id_a       TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    file_id_b       TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    cochange_count  INTEGER NOT NULL DEFAULT 0,
    cochange_score  REAL NOT NULL DEFAULT 0,
    UNIQUE(repo_id, file_id_a, file_id_b)
);

CREATE TABLE IF NOT EXISTS decisions (
    id              TEXT PRIMARY KEY,
    repo_id         TEXT NOT NULL,
    title           TEXT NOT NULL,
    context_text    TEXT,
    decision_text   TEXT NOT NULL,
    consequences    TEXT,
    files_affected  TEXT,
    created_at      TEXT NOT NULL,
    is_stale        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pr_analyses (
    id              TEXT PRIMARY KEY,
    repo_id         TEXT NOT NULL,
    pr_number       INTEGER NOT NULL,
    pr_title        TEXT,
    blast_radius_json TEXT NOT NULL,
    risk_score      REAL NOT NULL,
    analyzed_at     TEXT NOT NULL,
    UNIQUE(repo_id, pr_number)
);

CREATE TABLE IF NOT EXISTS llm_costs (
    id              TEXT PRIMARY KEY,
    repo_id         TEXT NOT NULL,
    file_path       TEXT,
    operation       TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0,
    called_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_costs_repo ON llm_costs(repo_id, called_at DESC);

CREATE TABLE IF NOT EXISTS index_checkpoints (
    id          TEXT PRIMARY KEY,
    repo_id     TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    error_msg   TEXT,
    updated_at  TEXT NOT NULL,
    UNIQUE(repo_id, file_path, stage)
);
"""
