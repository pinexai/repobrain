from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from ...config import RepomindConfig
from ...storage.sql import AsyncSQLiteDB
from ...storage.graph import GraphStore
from ...utils.hash_utils import repo_id

console = Console()


@click.command()
@click.option("--repo", default=".", help="Repo root")
def status_cmd(repo: str) -> None:
    """Show current index health, hotspots, and cost summary."""
    asyncio.run(_run_status(repo))


async def _run_status(repo: str) -> None:
    config = RepomindConfig(repo_path=Path(repo).resolve())
    rid = repo_id(config.repo_path)

    if not config.db_path.exists():
        console.print("[yellow]No index found. Run `repomind index` first.[/yellow]")
        return

    db = AsyncSQLiteDB(config.db_path)
    await db.connect()

    # File count
    rows = await db.fetchall("SELECT language, COUNT(*) as cnt FROM files WHERE repo_id=? GROUP BY language", (rid,))
    graph = GraphStore(config.graph_path)
    graph.load()

    console.print(f"\n[bold]repomind status — {config.repo_path.name}[/bold]\n")

    lang_table = Table("Language", "Files", box=box.SIMPLE)
    total = 0
    for row in rows:
        lang_table.add_row(row["language"], str(row["cnt"]))
        total += row["cnt"]
    console.print(lang_table)
    console.print(f"Total: {total} files | Graph: {graph.node_count()} nodes, {graph.edge_count()} edges\n")

    # Top 5 hotspots
    hotspots = await db.fetchall(
        """SELECT f.path, m.temporal_hotspot_score, m.owner_email
           FROM file_git_metrics m JOIN files f ON m.file_id = f.id
           WHERE f.repo_id = ?
           ORDER BY m.temporal_hotspot_score DESC LIMIT 5""",
        (rid,),
    )
    if hotspots:
        hs_table = Table("Top Hotspots", "Score", "Owner", box=box.SIMPLE)
        for h in hotspots:
            hs_table.add_row(h["path"].split("/")[-1], f"{h['temporal_hotspot_score']:.2f}", h["owner_email"])
        console.print(hs_table)

    # Cost summary
    cost_row = await db.fetchone(
        "SELECT SUM(cost_usd) as total, COUNT(*) as calls FROM llm_costs WHERE repo_id=?",
        (rid,),
    )
    if cost_row and cost_row["total"]:
        console.print(f"\nLLM Spend: [green]${cost_row['total']:.4f}[/green] ({cost_row['calls']} calls)")

    await db.close()
