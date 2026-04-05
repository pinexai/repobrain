"""
PRBlastRadiusAnalyzer — the flagship feature repowise entirely lacks.

Given a PR (set of changed files), compute:
1. Direct impact: files changed in the PR
2. Transitive impact: all files that depend on changed files (reverse graph traversal)
3. Risk score: centrality × temporal_hotspot × (1 + test_gap)
4. Co-change warnings: files historically coupled but missing from PR
5. Recommended reviewers: top owners of affected files
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ..graph.analyzer import GraphAnalyzer
from ..storage.graph import GraphStore
from ..storage.sql import AsyncSQLiteDB, FileRepository, GitMetricsRepository
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class FileRisk:
    file_path: str
    risk_score: float
    centrality: float
    temporal_hotspot: float
    owner_email: str
    impact_reason: str  # "direct_change" | "imports_changed" | "transitive"
    has_tests: bool = False


@dataclass
class CoChangeWarning:
    file_path: str
    cochanges_with: str  # file in PR
    cochange_score: float
    cochange_count: int
    message: str


@dataclass
class ReviewerRecommendation:
    email: str
    ownership_pct: float
    files_owned: list[str]


@dataclass
class PRImpactReport:
    pr_number: int | None
    pr_title: str
    changed_files: list[FileRisk]
    transitive_files: list[FileRisk]
    missing_cochange_files: list[CoChangeWarning]
    overall_risk_score: float
    recommended_reviewers: list[ReviewerRecommendation]
    test_gap_files: list[str]
    analyzed_at: str


class PRBlastRadiusAnalyzer:
    def __init__(
        self,
        graph_store: GraphStore,
        db: AsyncSQLiteDB,
        repo_id: str,
        github_token: str = "",
    ) -> None:
        self._graph = GraphAnalyzer(graph_store)
        self._graph_store = graph_store
        self._db = db
        self._file_repo = FileRepository(db)
        self._metrics_repo = GitMetricsRepository(db)
        self._repo_id = repo_id
        self._github_token = github_token

    async def analyze_files(
        self,
        changed_files: list[str],
        pr_number: int | None = None,
        pr_title: str = "",
        max_depth: int = 3,
    ) -> PRImpactReport:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()

        # Step 1: Score direct files
        direct_risks: list[FileRisk] = []
        for fp in changed_files:
            risk = await self._score_file(fp, "direct_change")
            direct_risks.append(risk)

        # Step 2: Transitive dependents (reverse graph traversal)
        transitive_set: set[str] = set()
        for fp in changed_files:
            dependents = self._graph.get_transitive_dependents(fp, max_depth)
            transitive_set |= dependents
        transitive_set -= set(changed_files)

        transitive_risks: list[FileRisk] = []
        for fp in sorted(transitive_set):
            risk = await self._score_file(fp, "transitive")
            transitive_risks.append(risk)

        # Sort by risk descending
        direct_risks.sort(key=lambda r: r.risk_score, reverse=True)
        transitive_risks.sort(key=lambda r: r.risk_score, reverse=True)

        # Step 3: Co-change warnings
        cochange_warnings = await self._find_cochange_warnings(changed_files)

        # Step 4: Recommended reviewers
        all_files = changed_files + list(transitive_set)
        reviewers = await self._recommend_reviewers(all_files)

        # Step 5: Test gap files
        test_gaps = await self._find_test_gaps(changed_files + list(transitive_set))

        # Step 6: Overall risk (weighted average of top files)
        all_scores = [r.risk_score for r in direct_risks + transitive_risks]
        overall = sum(sorted(all_scores, reverse=True)[:10]) / max(1, min(10, len(all_scores)))
        overall = min(10.0, overall * 10)  # normalize to 0-10

        return PRImpactReport(
            pr_number=pr_number,
            pr_title=pr_title,
            changed_files=direct_risks,
            transitive_files=transitive_risks[:50],  # cap at 50
            missing_cochange_files=cochange_warnings,
            overall_risk_score=round(overall, 2),
            recommended_reviewers=reviewers,
            test_gap_files=test_gaps,
            analyzed_at=now,
        )

    async def analyze_pr(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        max_depth: int = 3,
    ) -> PRImpactReport:
        """Fetch PR from GitHub API and analyze."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self._github_token:
            headers["Authorization"] = f"token {self._github_token}"

        async with httpx.AsyncClient() as client:
            # Get PR info
            pr_resp = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}",
                headers=headers,
            )
            pr_data = pr_resp.json()
            pr_title = pr_data.get("title", "")

            # Get PR files
            files_resp = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/files",
                headers=headers,
            )
            files_data = files_resp.json()
            changed_files = [f["filename"] for f in files_data]

        return await self.analyze_files(changed_files, pr_number, pr_title, max_depth)

    async def _score_file(self, file_path: str, reason: str) -> FileRisk:
        centrality = 0.0
        temporal_hotspot = 0.0
        owner_email = ""

        node_attrs = self._graph_store.get_node_attrs(file_path)
        if node_attrs:
            centrality = float(node_attrs.get("centrality", 0.0))

        file_rec = await self._file_repo.get_by_path(self._repo_id, file_path)
        if file_rec:
            metrics = await self._metrics_repo.get_by_file(file_rec["id"])
            if metrics:
                temporal_hotspot = metrics.get("temporal_hotspot_score", 0.0)
                owner_email = metrics.get("owner_email", "")

        risk_score = centrality * (1 + temporal_hotspot)
        return FileRisk(
            file_path=file_path,
            risk_score=risk_score,
            centrality=centrality,
            temporal_hotspot=temporal_hotspot,
            owner_email=owner_email,
            impact_reason=reason,
        )

    async def _find_cochange_warnings(self, changed_files: list[str]) -> list[CoChangeWarning]:
        warnings: list[CoChangeWarning] = []
        changed_set = set(changed_files)

        for fp in changed_files:
            file_rec = await self._file_repo.get_by_path(self._repo_id, fp)
            if not file_rec:
                continue
            partners = await self._metrics_repo.get_cochange_partners(
                file_rec["id"], self._repo_id, min_score=0.3
            )
            for partner in partners:
                partner_path = partner.get("partner_path", "")
                if partner_path and partner_path not in changed_set:
                    warnings.append(CoChangeWarning(
                        file_path=partner_path,
                        cochanges_with=fp,
                        cochange_score=partner.get("cochange_score", 0.0),
                        cochange_count=partner.get("cochange_count", 0),
                        message=(
                            f"{partner_path} historically changed with {fp} "
                            f"({partner.get('cochange_count', 0)}x) but is missing from this PR"
                        ),
                    ))

        return sorted(warnings, key=lambda w: w.cochange_score, reverse=True)

    async def _recommend_reviewers(self, files: list[str]) -> list[ReviewerRecommendation]:
        reviewer_files: dict[str, list[str]] = {}
        reviewer_scores: dict[str, float] = {}

        for fp in files:
            file_rec = await self._file_repo.get_by_path(self._repo_id, fp)
            if not file_rec:
                continue
            metrics = await self._metrics_repo.get_by_file(file_rec["id"])
            if metrics and metrics.get("owner_email"):
                email = metrics["owner_email"]
                reviewer_files.setdefault(email, []).append(fp)
                reviewer_scores[email] = reviewer_scores.get(email, 0.0) + metrics.get("ownership_pct", 0.0)

        recommendations = [
            ReviewerRecommendation(
                email=email,
                ownership_pct=round(score / max(1, len(reviewer_files[email])), 2),
                files_owned=reviewer_files[email],
            )
            for email, score in reviewer_scores.items()
        ]
        return sorted(recommendations, key=lambda r: r.ownership_pct, reverse=True)[:5]

    async def _find_test_gaps(self, files: list[str]) -> list[str]:
        gaps: list[str] = []
        for fp in files:
            basename = Path(fp).stem
            test_patterns = [f"test_{basename}", f"{basename}_test", f"{basename}.test", f"{basename}.spec"]
            has_test = False
            for pattern in test_patterns:
                rows = await self._db.fetchall(
                    "SELECT 1 FROM files WHERE repo_id = ? AND path LIKE ?",
                    (self._repo_id, f"%{pattern}%"),
                )
                if rows:
                    has_test = True
                    break
            if not has_test and not any(t in fp for t in ["test_", "_test", ".test", ".spec"]):
                gaps.append(fp)
        return gaps
