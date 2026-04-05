from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console

from ...config import RepomindConfig

console = Console()


@click.command()
@click.option("--mcp-port", default=8766, show_default=True)
@click.option("--webhook-port", default=8765, show_default=True)
@click.option("--mcp-only", is_flag=True, default=False)
@click.option("--webhook-only", is_flag=True, default=False)
@click.option("--repo", default=".", help="Repo root")
def serve_cmd(
    mcp_port: int,
    webhook_port: int,
    mcp_only: bool,
    webhook_only: bool,
    repo: str,
) -> None:
    """Start MCP server and/or webhook server."""
    config = RepomindConfig(repo_path=Path(repo).resolve())
    config.mcp.port = mcp_port
    config.webhook.port = webhook_port
    asyncio.run(_run_serve(config, mcp_only, webhook_only))


async def _run_serve(config: RepomindConfig, mcp_only: bool, webhook_only: bool) -> None:
    from ...mcp.server import mcp, start_server

    await start_server(config)

    tasks = []
    if not webhook_only:
        console.print(f"[bold green]MCP server starting on port {config.mcp.port}[/bold green]")
        # fastmcp run_async
        tasks.append(asyncio.create_task(
            mcp.run_async(transport="stdio")
        ))

    if not mcp_only:
        from ...webhook.server import create_app
        import uvicorn
        app = create_app(config)
        console.print(f"[bold blue]Webhook server starting on port {config.webhook.port}[/bold blue]")
        server = uvicorn.Server(uvicorn.Config(app, port=config.webhook.port, log_level="warning"))
        tasks.append(asyncio.create_task(server.serve()))

    if tasks:
        await asyncio.gather(*tasks)
