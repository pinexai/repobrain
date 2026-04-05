"""
CoChangeAnalyzer — detects files that change together without explicit import links.
These are "hidden coupling" pairs that pure static analysis misses.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp, log as ln

from .history import CommitRecord
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class CoChangePair:
    file_a: str
    file_b: str
    cochange_count: int
    cochange_score: float  # temporal-weighted, not just raw count


class CoChangeAnalyzer:
    """
    Temporal-weighted co-change detection.
    Repowise ignores commit age here too — we fix that.
    """

    def __init__(
        self,
        halflife_days: float = 180.0,
        window_days: int = 90,
        min_cochanges: int = 2,
    ) -> None:
        self._halflife = halflife_days
        self._window_days = window_days
        self._min_cochanges = min_cochanges

    def analyze(self, commits: list[CommitRecord]) -> list[CoChangePair]:
        now = datetime.now(timezone.utc)
        pair_counts: dict[tuple[str, str], int] = defaultdict(int)
        pair_scores: dict[tuple[str, str], float] = defaultdict(float)

        for commit in commits:
            files = sorted(set(commit.files_changed))
            if len(files) < 2:
                continue

            try:
                authored_at = datetime.fromisoformat(commit.authored_at)
                if authored_at.tzinfo is None:
                    authored_at = authored_at.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (now - authored_at).total_seconds() / 86400)
            except (ValueError, OSError):
                age_days = 365.0

            # Only count commits within the configured window
            if age_days > self._window_days:
                continue

            decay = exp(-ln(2) * age_days / self._halflife)

            # Generate all pairs in this commit
            for i, fa in enumerate(files):
                for fb in files[i + 1:]:
                    key = (fa, fb)
                    pair_counts[key] += 1
                    pair_scores[key] += decay

        results: list[CoChangePair] = []
        for (fa, fb), count in pair_counts.items():
            if count >= self._min_cochanges:
                results.append(CoChangePair(
                    file_a=fa,
                    file_b=fb,
                    cochange_count=count,
                    cochange_score=pair_scores[(fa, fb)],
                ))

        return sorted(results, key=lambda p: p.cochange_score, reverse=True)
