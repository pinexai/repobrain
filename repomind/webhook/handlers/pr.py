from __future__ import annotations

from ...config import RepomindConfig
from ...utils.logging import get_logger

log = get_logger(__name__)


class PREventHandler:
    def __init__(self, config: RepomindConfig) -> None:
        self._config = config

    async def handle(self, payload: dict) -> None:
        action = payload.get("action", "")
        if action not in ("opened", "synchronize", "reopened"):
            return

        pr = payload.get("pull_request", {})
        pr_number = pr.get("number")
        pr_title = pr.get("title", "")
        changed_files = [f.get("filename", "") for f in payload.get("files", [])]

        if not changed_files:
            # files not in webhook payload; skip
            return

        log.info("pr_analysis_start", pr=pr_number, files=len(changed_files))

        try:
            from ...storage.graph import GraphStore
            from ...storage.sql import AsyncSQLiteDB
            from ...git.pr_analyzer import PRBlastRadiusAnalyzer
            from ...utils.hash_utils import repo_id

            rid = repo_id(self._config.repo_path)
            db = AsyncSQLiteDB(self._config.db_path)
            graph_store = GraphStore(self._config.graph_path)
            await db.connect()
            graph_store.load()

            analyzer = PRBlastRadiusAnalyzer(
                graph_store=graph_store,
                db=db,
                repo_id=rid,
                github_token=self._config.github_token,
            )
            report = await analyzer.analyze_files(changed_files, pr_number, pr_title)
            await db.close()

            if self._config.webhook.post_pr_comments and self._config.github_token:
                await self._post_comment(payload, report)

        except Exception as e:
            log.error("pr_analysis_failed", pr=pr_number, error=str(e))

    async def _post_comment(self, payload: dict, report) -> None:
        """Post blast radius analysis as a GitHub PR comment."""
        try:
            import httpx
            repo_full = payload.get("repository", {}).get("full_name", "")
            pr_number = payload.get("pull_request", {}).get("number")
            if not repo_full or not pr_number:
                return

            risk_emoji = "🔴" if report.overall_risk_score >= 7 else "🟡" if report.overall_risk_score >= 4 else "🟢"
            body = (
                f"## repomind Blast Radius Analysis {risk_emoji}\n\n"
                f"**Risk Score:** {report.overall_risk_score}/10\n"
                f"**Direct files:** {len(report.changed_files)} | "
                f"**Transitive:** {len(report.transitive_files)}\n\n"
            )
            if report.missing_cochange_files:
                body += "### ⚠️ Co-change Warnings\n"
                for w in report.missing_cochange_files[:3]:
                    body += f"- {w.message}\n"
                body += "\n"
            if report.recommended_reviewers:
                body += "### 👥 Suggested Reviewers\n"
                for r in report.recommended_reviewers[:3]:
                    body += f"- @{r.email.split('@')[0]} ({r.ownership_pct*100:.0f}% ownership)\n"

            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.github.com/repos/{repo_full}/issues/{pr_number}/comments",
                    headers={
                        "Authorization": f"token {self._config.github_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    json={"body": body},
                )
        except Exception as e:
            log.warning("pr_comment_failed", error=str(e))
