from __future__ import annotations

from pathlib import Path

import pytest

from repomind.storage.sql import AsyncSQLiteDB, FileRepository, GitMetricsRepository


@pytest.fixture
async def db(tmp_path: Path) -> AsyncSQLiteDB:
    db = AsyncSQLiteDB(tmp_path / "test.db")
    await db.connect()
    yield db
    await db.close()


class TestFileRepository:
    async def test_upsert_creates_file(self, db: AsyncSQLiteDB):
        repo = FileRepository(db)
        file_id = await repo.upsert(
            repo_id="repo1",
            path="src/main.py",
            language="python",
            size_bytes=1000,
            content_hash="abc123",
        )
        assert file_id

        rec = await repo.get_by_path("repo1", "src/main.py")
        assert rec is not None
        assert rec["language"] == "python"
        assert rec["content_hash"] == "abc123"

    async def test_upsert_updates_existing(self, db: AsyncSQLiteDB):
        repo = FileRepository(db)
        id1 = await repo.upsert("repo1", "a.py", "python", 100, "hash1")
        id2 = await repo.upsert("repo1", "a.py", "python", 200, "hash2")
        assert id1 == id2  # same ID

        rec = await repo.get_by_path("repo1", "a.py")
        assert rec["content_hash"] == "hash2"
        assert rec["size_bytes"] == 200

    async def test_hash_for_change_detection(self, db: AsyncSQLiteDB):
        repo = FileRepository(db)
        await repo.upsert("repo1", "b.py", "python", 50, "oldhash")
        stored = await repo.get_content_hash("repo1", "b.py")
        assert stored == "oldhash"


class TestGitMetricsRepository:
    async def test_upsert_and_percentile_refresh(self, db: AsyncSQLiteDB):
        """Verify percentile_rank is refreshed after upsert — the fix repowise misses."""
        file_repo = FileRepository(db)
        metrics_repo = GitMetricsRepository(db)

        # Create two files
        id1 = await file_repo.upsert("r", "hot.py", "python", 100, "h1")
        id2 = await file_repo.upsert("r", "cold.py", "python", 100, "h2")

        await metrics_repo.upsert(id1, hotspot_score=10.0, temporal_hotspot_score=10.0,
                                   owner_email="a@co.com", ownership_pct=1.0, churn_count=50)
        await metrics_repo.upsert(id2, hotspot_score=1.0, temporal_hotspot_score=1.0,
                                   owner_email="b@co.com", ownership_pct=1.0, churn_count=5)

        m1 = await metrics_repo.get_by_file(id1)
        m2 = await metrics_repo.get_by_file(id2)

        assert m1 is not None and m2 is not None
        # hot.py should have higher percentile rank
        assert m1["percentile_rank"] > m2["percentile_rank"]
