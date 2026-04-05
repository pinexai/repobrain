from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from repomind.git.pr_analyzer import PRBlastRadiusAnalyzer, FileRisk


@pytest.fixture
async def mock_analyzer(tmp_path: Path):
    from repomind.storage.graph import GraphStore
    from repomind.storage.sql import AsyncSQLiteDB

    db = AsyncSQLiteDB(tmp_path / "test.db")
    await db.connect()
    graph = GraphStore(tmp_path / "graph.graphml")
    # Set up a minimal graph
    graph.add_node("src/api.py", type="file", centrality=0.8)
    graph.add_node("src/models.py", type="file", centrality=0.5)
    graph.add_node("src/utils.py", type="file", centrality=0.2)
    graph.add_edge("src/api.py", "src/models.py")
    graph.add_edge("src/models.py", "src/utils.py")

    analyzer = PRBlastRadiusAnalyzer(
        graph_store=graph,
        db=db,
        repo_id="test-repo",
    )
    yield analyzer
    await db.close()


class TestPRBlastRadiusAnalyzer:
    async def test_direct_files_in_report(self, mock_analyzer: PRBlastRadiusAnalyzer):
        report = await mock_analyzer.analyze_files(
            changed_files=["src/api.py"],
            pr_title="Add API endpoint",
        )
        direct_paths = [r.file_path for r in report.changed_files]
        assert "src/api.py" in direct_paths

    async def test_transitive_files_detected(self, mock_analyzer: PRBlastRadiusAnalyzer):
        # src/models.py depends on src/utils.py
        # Changing src/models.py should surface src/* that depends on it
        report = await mock_analyzer.analyze_files(
            changed_files=["src/utils.py"],
        )
        # src/api.py transitively imports src/utils.py (via models.py)
        transitive_paths = [r.file_path for r in report.transitive_files]
        assert "src/api.py" in transitive_paths or "src/models.py" in transitive_paths

    async def test_risk_score_bounded(self, mock_analyzer: PRBlastRadiusAnalyzer):
        report = await mock_analyzer.analyze_files(
            changed_files=["src/api.py", "src/models.py"],
        )
        assert 0.0 <= report.overall_risk_score <= 10.0

    async def test_empty_pr(self, mock_analyzer: PRBlastRadiusAnalyzer):
        report = await mock_analyzer.analyze_files(changed_files=[])
        assert report.changed_files == []
        assert report.overall_risk_score == 0.0

    async def test_report_has_analyzed_at(self, mock_analyzer: PRBlastRadiusAnalyzer):
        report = await mock_analyzer.analyze_files(changed_files=["src/api.py"])
        assert report.analyzed_at
