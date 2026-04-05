from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from ...config import RepomindConfig
from ...core.indexer import AsyncIndexingPipeline, IndexingProgress

console = Console()


@click.command()
@click.argument("repo_path", default=".", required=False)
@click.option("--full", "incremental", flag_value=False, default=True, help="Force full re-index")
@click.option("--incremental", "incremental", flag_value=True, default=True, help="Only changed files")
@click.option("--max-commits", default=None, type=int, help="Override git history depth")
@click.option("--concurrency", default=None, type=int, help="Worker pool size")
@click.option("--no-docs", is_flag=True, default=False, help="Skip LLM doc generation")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be indexed")
@click.pass_context
def index_cmd(
    ctx: click.Context,
    repo_path: str,
    incremental: bool,
    max_commits: int | None,
    concurrency: int | None,
    no_docs: bool,
    dry_run: bool,
) -> None:
    """Index a repository for codebase intelligence."""
    config = RepomindConfig(repo_path=Path(repo_path).resolve())
    if max_commits:
        config.git.max_commits = max_commits
    if concurrency:
        config.indexing.worker_processes = concurrency

    if dry_run:
        from ...utils.file_utils import walk_repo
        files = walk_repo(
            config.repo_path,
            config.indexing.exclude_patterns,
            config.indexing.languages,
            config.indexing.max_file_size_bytes,
        )
        console.print(f"[bold]Dry run: would index [cyan]{len(files)}[/cyan] files[/bold]")
        for f in files[:20]:
            console.print(f"  {f.relative_to(config.repo_path)}")
        if len(files) > 20:
            console.print(f"  ... and {len(files) - 20} more")
        return

    asyncio.run(_run_index(config, incremental))


async def _run_index(config: RepomindConfig, incremental: bool) -> None:
    pipeline = AsyncIndexingPipeline(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("• Cost: [green]${task.fields[cost]:.3f}[/green]"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Starting...", total=100, cost=0.0)

        def on_progress(p: IndexingProgress) -> None:
            progress.update(
                task,
                description=p.stage,
                completed=int(p.pct),
                total=100,
                cost=p.cost_so_far,
            )

        pipeline.on_progress(on_progress)
        await pipeline.run(incremental=incremental)

    console.print("[bold green]✓ Indexing complete![/bold green]")
