from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from ...config import RepomindConfig
from ...storage.sql import AsyncSQLiteDB
from ...utils.hash_utils import repo_id

console = Console()


@click.command()
@click.argument("query_text")
@click.option("--repo", default=".", help="Repo root")
@click.option("--top-k", default=10, show_default=True)
def query_cmd(query_text: str, repo: str, top_k: int) -> None:
    """Natural language query against the indexed codebase."""
    asyncio.run(_run_query(repo, query_text, top_k))


async def _run_query(repo: str, query_text: str, top_k: int) -> None:
    config = RepomindConfig(repo_path=Path(repo).resolve())
    rid = repo_id(config.repo_path)

    db = AsyncSQLiteDB(config.db_path)
    await db.connect()

    like = f"%{query_text}%"
    rows = await db.fetchall(
        """SELECT DISTINCT f.path, f.language, s.name, s.kind
           FROM files f
           LEFT JOIN symbols s ON s.file_id = f.id
           WHERE f.repo_id = ? AND (f.path LIKE ? OR LOWER(s.name) LIKE ?)
           LIMIT ?""",
        (rid, like, like.lower(), top_k),
    )

    if not rows:
        console.print(f"[yellow]No results for '{query_text}'[/yellow]")
    else:
        console.print(f"\n[bold]Results for '{query_text}':[/bold]\n")
        for row in rows:
            sym = f"  [{row['kind']}] {row['name']}" if row["name"] else ""
            console.print(f"[cyan]{row['path']}[/cyan]{sym}")

    await db.close()
