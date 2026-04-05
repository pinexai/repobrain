from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from ...config import RepomindConfig
from ...storage.sql import AsyncSQLiteDB
from ...utils.hash_utils import repo_id

console = Console()


@click.command()
@click.option("--since", default=None, help="Filter from date (ISO format)")
@click.option("--by", "group_by", type=click.Choice(["operation", "model", "day"]), default="operation")
@click.option("--repo", default=".", help="Repo root")
def costs_cmd(since: str | None, group_by: str, repo: str) -> None:
    """Show LLM cost breakdown powered by tokenspy-compatible tracking."""
    asyncio.run(_run_costs(repo, since, group_by))


async def _run_costs(repo: str, since: str | None, group_by: str) -> None:
    config = RepomindConfig(repo_path=Path(repo).resolve())
    rid = repo_id(config.repo_path)

    if not config.db_path.exists():
        console.print("[yellow]No index found. Run `repomind index` first.[/yellow]")
        return

    db = AsyncSQLiteDB(config.db_path)
    await db.connect()

    if group_by == "operation":
        rows = await db.fetchall(
            """SELECT operation, COUNT(*) as calls,
               SUM(input_tokens+output_tokens) as tokens,
               SUM(cost_usd) as cost
               FROM llm_costs WHERE repo_id=? GROUP BY operation ORDER BY cost DESC""",
            (rid,),
        )
        table = Table("Operation", "Calls", "Tokens", "Cost (USD)", box=box.ROUNDED)
        total_cost = 0.0
        for row in rows:
            table.add_row(row["operation"], str(row["calls"]), f"{row['tokens']:,}", f"${row['cost']:.4f}")
            total_cost += row["cost"]
        console.print(table)
        console.print(f"\n[bold]Total: [green]${total_cost:.4f}[/green][/bold]")

    elif group_by == "model":
        rows = await db.fetchall(
            "SELECT model, COUNT(*) as calls, SUM(cost_usd) as cost FROM llm_costs WHERE repo_id=? GROUP BY model ORDER BY cost DESC",
            (rid,),
        )
        table = Table("Model", "Calls", "Cost (USD)", box=box.ROUNDED)
        for row in rows:
            table.add_row(row["model"], str(row["calls"]), f"${row['cost']:.4f}")
        console.print(table)

    elif group_by == "day":
        rows = await db.fetchall(
            """SELECT DATE(called_at) as day, COUNT(*) as calls, SUM(cost_usd) as cost
               FROM llm_costs WHERE repo_id=? GROUP BY day ORDER BY day DESC LIMIT 30""",
            (rid,),
        )
        table = Table("Day", "Calls", "Cost (USD)", box=box.ROUNDED)
        for row in rows:
            table.add_row(row["day"], str(row["calls"]), f"${row['cost']:.4f}")
        console.print(table)

    await db.close()
