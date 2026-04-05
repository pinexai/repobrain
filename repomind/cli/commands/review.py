from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from ...config import RepomindConfig
from ...git.pr_analyzer import PRBlastRadiusAnalyzer
from ...storage.graph import GraphStore
from ...storage.sql import AsyncSQLiteDB
from ...utils.hash_utils import repo_id

console = Console()


@click.command()
@click.argument("pr_or_branch")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "markdown"]), default="table")
@click.option("--max-depth", default=3, show_default=True, help="Transitive traversal depth")
@click.option("--repo", default=".", help="Repo root")
@click.pass_context
def review_cmd(
    ctx: click.Context,
    pr_or_branch: str,
    fmt: str,
    max_depth: int,
    repo: str,
) -> None:
    """Analyze blast radius of a PR or branch before merge."""
    asyncio.run(_run_review(repo, pr_or_branch, fmt, max_depth))


async def _run_review(repo: str, pr_or_branch: str, fmt: str, max_depth: int) -> None:
    config = RepomindConfig(repo_path=Path(repo).resolve())
    rid = repo_id(config.repo_path)

    db = AsyncSQLiteDB(config.db_path)
    graph_store = GraphStore(config.graph_path)
    await db.connect()
    graph_store.load()

    analyzer = PRBlastRadiusAnalyzer(
        graph_store=graph_store,
        db=db,
        repo_id=rid,
        github_token=config.github_token,
    )

    # Determine if it's a PR number or branch name
    changed_files: list[str] = []
    pr_number: int | None = None
    pr_title = ""

    if pr_or_branch.isdigit():
        pr_number = int(pr_or_branch)
        # Try to get files from git diff vs main
        changed_files = await _get_pr_files_github(config, pr_number)
        pr_title = f"PR #{pr_number}"
    else:
        # Branch: get diff vs main
        changed_files = _get_branch_diff(config.repo_path, pr_or_branch)
        pr_title = f"Branch: {pr_or_branch}"

    if not changed_files:
        console.print(f"[yellow]No changed files found for {pr_or_branch}[/yellow]")
        await db.close()
        return

    report = await analyzer.analyze_files(changed_files, pr_number, pr_title, max_depth)
    await db.close()

    if fmt == "json":
        click.echo(json.dumps({
            "risk_score": report.overall_risk_score,
            "direct_files": len(report.changed_files),
            "transitive_files": len(report.transitive_files),
            "cochange_warnings": len(report.missing_cochange_files),
        }, indent=2))
        return

    # Rich table output
    risk_color = "red" if report.overall_risk_score >= 7 else "yellow" if report.overall_risk_score >= 4 else "green"
    console.print(f"\n[bold]PR Analysis: {pr_title}[/bold]")
    console.print(f"Overall Risk: [{risk_color}]{report.overall_risk_score}/10 ({_risk_label(report.overall_risk_score)})[/{risk_color}]")
    console.print(f"Direct: {len(report.changed_files)} files  |  Transitive: {len(report.transitive_files)} files\n")

    if report.missing_cochange_files:
        console.print("[yellow]⚠ Co-change Warnings:[/yellow]")
        for w in report.missing_cochange_files[:5]:
            console.print(f"  • {w.message}")
        console.print()

    if report.recommended_reviewers:
        console.print("[bold]Recommended Reviewers:[/bold]")
        for r in report.recommended_reviewers:
            console.print(f"  • {r.email} ({r.ownership_pct*100:.0f}% ownership)")
        console.print()

    table = Table(title="Highest Risk Files", box=box.ROUNDED)
    table.add_column("File", style="cyan")
    table.add_column("Risk", justify="right")
    table.add_column("Owner", style="dim")
    table.add_column("Reason")

    for r in (report.changed_files + report.transitive_files)[:10]:
        color = "red" if r.risk_score > 0.5 else "yellow"
        table.add_row(
            r.file_path.split("/")[-1],
            f"[{color}]{r.risk_score:.3f}[/{color}]",
            r.owner_email or "unknown",
            r.impact_reason,
        )
    console.print(table)


async def _get_pr_files_github(config: RepomindConfig, pr_number: int) -> list[str]:
    if not config.github_token:
        return []
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # Would need repo owner/name from config or git remote
            return []
    except Exception:
        return []


def _get_branch_diff(repo_path: Path, branch: str) -> list[str]:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", f"main...{branch}"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        return [str(repo_path / f) for f in result.stdout.strip().splitlines() if f]
    except Exception:
        return []


def _risk_label(score: float) -> str:
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"
