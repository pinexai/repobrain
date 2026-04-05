"""
TemporalMetricsCalculator — THE key improvement over repowise's git analytics.

Repowise weighs all commits equally regardless of age.
We use exponential decay: recent commits matter exponentially more.

score += exp(-ln(2) * age_days / halflife) * min(lines_changed / 100, 3.0)

With halflife=180 days:
  - commit today:    weight = 1.0
  - commit 6mo ago:  weight = 0.5
  - commit 1yr ago:  weight = 0.25
  - commit 2yr ago:  weight = 0.0625
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import exp, log as ln

from .history import CommitRecord, FileHistory
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class FileMetrics:
    file_path: str
    hotspot_score: float = 0.0          # raw cumulative score (all commits equal)
    temporal_hotspot_score: float = 0.0  # decay-weighted score (recent > old)
    churn_count: int = 0
    owner_email: str = ""
    ownership_pct: float = 0.0
    ownership_map: dict[str, float] = field(default_factory=dict)


class TemporalMetricsCalculator:
    """
    Computes decay-weighted hotspot scores and temporal ownership.
    halflife_days: number of days after which a commit's weight is halved.
    """

    def __init__(self, halflife_days: float = 180.0) -> None:
        self._halflife = halflife_days

    def compute(self, history: FileHistory) -> FileMetrics:
        metrics = FileMetrics(file_path=history.file_path)
        if not history.commits:
            return metrics

        now = datetime.now(timezone.utc)
        author_scores: dict[str, float] = {}
        raw_score = 0.0
        temporal_score = 0.0

        for commit in history.commits:
            try:
                authored_at = datetime.fromisoformat(commit.authored_at)
                if authored_at.tzinfo is None:
                    authored_at = authored_at.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - authored_at).total_seconds() / 86400)
            except (ValueError, OSError):
                age_days = 365.0

            # Complexity multiplier: larger diffs = higher weight (capped at 3x)
            complexity = min(commit.lines_changed / 100.0, 3.0) if commit.lines_changed > 0 else 0.1

            # Exponential decay weight
            decay = exp(-ln(2) * age_days / self._halflife)

            raw_score += complexity
            temporal_score += decay * complexity

            # Track temporal ownership
            author = commit.author_email or "unknown"
            author_scores[author] = author_scores.get(author, 0.0) + decay * complexity

        metrics.hotspot_score = raw_score
        metrics.temporal_hotspot_score = temporal_score
        metrics.churn_count = len(history.commits)

        # Normalize ownership percentages
        total = sum(author_scores.values())
        if total > 0:
            normalized = {a: s / total for a, s in author_scores.items()}
            metrics.ownership_map = normalized
            top_author = max(normalized, key=lambda k: normalized[k])
            metrics.owner_email = top_author
            metrics.ownership_pct = normalized[top_author]

        return metrics

    def compute_batch(self, histories: list[FileHistory]) -> list[FileMetrics]:
        return [self.compute(h) for h in histories]
