from __future__ import annotations

import click
from rich.console import Console

from ..utils.logging import configure_logging

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.option("--repo", default=".", show_default=True, help="Repo root path")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, repo: str) -> None:
    """repomind — codebase intelligence that thinks ahead."""
    configure_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["repo"] = repo
    ctx.obj["verbose"] = verbose


from .commands.index import index_cmd  # noqa: E402
from .commands.review import review_cmd  # noqa: E402
from .commands.serve import serve_cmd  # noqa: E402
from .commands.status import status_cmd  # noqa: E402
from .commands.costs import costs_cmd  # noqa: E402
from .commands.query import query_cmd  # noqa: E402

cli.add_command(index_cmd, "index")
cli.add_command(review_cmd, "review")
cli.add_command(serve_cmd, "serve")
cli.add_command(status_cmd, "status")
cli.add_command(costs_cmd, "costs")
cli.add_command(query_cmd, "query")
