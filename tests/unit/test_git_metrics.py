from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from repomind.git.history import CommitRecord, FileHistory
from repomind.git.metrics import TemporalMetricsCalculator


def make_commit(days_ago: int, lines_changed: int = 50, email: str = "alice@co.com") -> CommitRecord:
    authored_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return CommitRecord(
        sha="abc" + str(days_ago),
        author_email=email,
        authored_at=authored_at,
        message_summary="fix: something",
        files_changed=["main.py"],
        lines_added=lines_changed // 2,
        lines_deleted=lines_changed // 2,
    )


class TestTemporalMetrics:
    def test_recent_commits_score_higher(self):
        calc = TemporalMetricsCalculator(halflife_days=180.0)

        recent = FileHistory(file_path="a.py", commits=[make_commit(1)])
        old = FileHistory(file_path="b.py", commits=[make_commit(365)])

        m_recent = calc.compute(recent)
        m_old = calc.compute(old)

        assert m_recent.temporal_hotspot_score > m_old.temporal_hotspot_score

    def test_temporal_decay_formula(self):
        """Commit 180 days ago should have weight ~0.5 (half-life)."""
        from math import exp, log
        calc = TemporalMetricsCalculator(halflife_days=180.0)
        history = FileHistory(file_path="x.py", commits=[make_commit(180)])
        m = calc.compute(history)
        # complexity = min(50/100, 3.0) = 0.5
        # decay = exp(-ln(2) * 180 / 180) = 0.5
        expected = 0.5 * 0.5  # 0.25
        assert abs(m.temporal_hotspot_score - expected) < 0.05

    def test_ownership_attributed_to_top_contributor(self):
        calc = TemporalMetricsCalculator()
        history = FileHistory(file_path="x.py", commits=[
            make_commit(1, 100, "alice@co.com"),
            make_commit(2, 100, "alice@co.com"),
            make_commit(3, 100, "bob@co.com"),
        ])
        m = calc.compute(history)
        assert m.owner_email == "alice@co.com"
        assert m.ownership_pct > 0.5

    def test_empty_history(self):
        calc = TemporalMetricsCalculator()
        m = calc.compute(FileHistory(file_path="x.py"))
        assert m.hotspot_score == 0.0
        assert m.temporal_hotspot_score == 0.0

    def test_raw_vs_temporal_scores_differ(self):
        """Raw (equal-weight) and temporal scores should differ for old commits."""
        calc = TemporalMetricsCalculator(halflife_days=180.0)
        history = FileHistory(file_path="x.py", commits=[
            make_commit(1),
            make_commit(730),  # 2 years ago
        ])
        m = calc.compute(history)
        assert m.hotspot_score != m.temporal_hotspot_score
