#!/usr/bin/env python3
"""Generate terminal screenshots as SVG for repobrain documentation."""
from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.text import Text
from rich import box
from pathlib import Path

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)


def make_console(width: int = 100) -> Console:
    return Console(record=True, width=width, force_terminal=True)


# ── Screenshot 1: repobrain index ─────────────────────────────────────────────
def screenshot_index() -> None:
    c = make_console()
    c.print()
    c.print(Panel.fit(
        "[bold cyan]repobrain[/] [white]index /path/to/myapp[/]",
        border_style="bright_blue",
    ))
    c.print()

    stages = [
        ("Discovery",      "✓", "green",  "Found [bold]1,247[/] files in 3 languages"),
        ("Parse",          "✓", "green",  "Parsed [bold]1,247[/] files  (ProcessPoolExecutor × 8)"),
        ("Graph Build",    "✓", "green",  "[bold]14,382[/] nodes · [bold]51,204[/] edges"),
        ("Git Analysis",   "✓", "green",  "[bold]8,420[/] commits · decay halflife 180 days"),
        ("Embedding",      "✓", "green",  "[bold]1,247[/] files embedded"),
        ("Doc Generation", "◉", "yellow", "Generating docs … [bold]623[/]/1,247"),
        ("Atomic Commit",  "○", "dim",    "Waiting"),
    ]

    for stage, icon, color, detail in stages:
        c.print(f"  [{color}]{icon}[/] [bold]{stage:<18}[/] {detail}")

    c.print()
    c.print("  [bright_blue][=============================>          ][/]  [bold]50%[/]  "
            "Stage: [yellow]Generating Docs[/]  "
            "Files: [bold]623/1,247[/]  "
            "Cost: [green]$0.41[/]  "
            "Elapsed: [dim]2m 14s[/]")
    c.print()

    c.save_svg(str(OUT / "screenshot-index.svg"), title="repobrain index")
    print("✓ screenshot-index.svg")


# ── Screenshot 2: repobrain status ────────────────────────────────────────────
def screenshot_status() -> None:
    c = make_console()
    c.print()
    c.print(Panel.fit(
        "[bold cyan]repobrain[/] [white]status[/]  —  [dim]myapp  ·  1,247 files indexed[/]",
        border_style="bright_blue",
    ))
    c.print()

    # Health row
    health = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    health.add_column(style="dim")
    health.add_column(style="bold green")
    health.add_row("SQLite",   "1,247 records")
    health.add_row("LanceDB",  "1,247 vectors")
    health.add_row("Graph",    "14,382 nodes  ·  51,204 edges")
    health.add_row("Consistent", "[bold green]✓ YES[/bold green]")
    c.print("  [bold]Index Health[/]")
    c.print(health)

    # Hotspots
    t = Table(
        title="🔥  Top Hotspots  (temporal decay · halflife 180d)",
        box=box.ROUNDED,
        border_style="bright_blue",
        header_style="bold cyan",
        show_lines=True,
    )
    t.add_column("Rank", justify="right", style="dim")
    t.add_column("File", style="bold white")
    t.add_column("Hotspot Score", justify="right")
    t.add_column("Percentile", justify="right")
    t.add_column("Owner", style="cyan")
    t.add_column("Churn (90d)", justify="right")

    rows = [
        ("1", "src/auth/tokens.py",         "[red]9.2[/]",    "[red]99th[/]",   "alice@co.com", "47"),
        ("2", "src/api/endpoints.py",        "[red]8.7[/]",    "[red]98th[/]",   "bob@co.com",   "39"),
        ("3", "src/models/user.py",          "[yellow]7.4[/]", "[yellow]94th[/]","alice@co.com", "31"),
        ("4", "src/billing/invoice.py",      "[yellow]6.9[/]", "[yellow]91st[/]","carol@co.com", "28"),
        ("5", "src/notifications/email.py",  "[yellow]5.8[/]", "[yellow]85th[/]","bob@co.com",   "22"),
    ]
    for row in rows:
        t.add_row(*row)
    c.print(t)
    c.print()
    c.save_svg(str(OUT / "screenshot-status.svg"), title="repobrain status")
    print("✓ screenshot-status.svg")


# ── Screenshot 3: repobrain review ────────────────────────────────────────────
def screenshot_review() -> None:
    c = make_console()
    c.print()
    c.print(Panel.fit(
        "[bold cyan]repobrain[/] [white]review 42[/]  —  [dim]Add OAuth2 login flow[/]",
        border_style="bright_blue",
    ))
    c.print()

    # Direct files
    direct = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", title="📂  Direct Changes  (3 files)")
    direct.add_column("File", style="bold white")
    direct.add_column("Risk", justify="right")
    direct.add_column("Centrality", justify="right")
    direct.add_column("Owner")
    direct.add_column("Tests?", justify="center")
    direct.add_row("src/auth/login.py",   "[red]8.4[/]",    "0.71", "alice@co.com", "[green]✓[/]")
    direct.add_row("src/auth/tokens.py",  "[red]7.9[/]",    "0.65", "alice@co.com", "[red]✗[/]")
    direct.add_row("src/models/user.py",  "[yellow]6.1[/]", "0.58", "bob@co.com",   "[green]✓[/]")
    c.print(direct)
    c.print()

    # Transitive
    trans = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", title="🔗  Transitive Dependents  (8 files)")
    trans.add_column("File", style="white")
    trans.add_column("Risk", justify="right")
    trans.add_column("Via", style="dim")
    trans.add_row("src/api/endpoints.py",        "[yellow]5.3[/]", "imports src/auth/login.py")
    trans.add_row("src/middleware/auth.py",       "[yellow]4.8[/]", "imports src/auth/tokens.py")
    trans.add_row("src/tests/test_login.py",      "[green]2.1[/]",  "imports src/auth/login.py")
    trans.add_row("[dim]+ 5 more …[/dim]",        "[dim]—[/dim]",   "")
    c.print(trans)
    c.print()

    # Co-change warning
    c.print(Panel(
        "[yellow]⚠[/]  [bold]src/auth/middleware.py[/] is historically changed with [bold]src/auth/login.py[/]\n"
        "   [dim]Co-change score: 0.78  (changed together 78% of the time)[/dim]\n"
        "   [yellow]Not included in this PR — review recommended.[/yellow]",
        title="[bold yellow]Co-change Warning[/bold yellow]",
        border_style="yellow",
    ))
    c.print()
    c.print("  [bold]Recommended Reviewers:[/]  [cyan]alice@co.com[/] · [cyan]bob@co.com[/]")
    c.print()
    c.print(Panel.fit(
        "  Overall Risk Score:  [bold red]7.8 / 10.0[/]  [red][HIGH][/]  ",
        border_style="red",
    ))
    c.print()
    c.save_svg(str(OUT / "screenshot-review.svg"), title="repobrain review 42")
    print("✓ screenshot-review.svg")


# ── Screenshot 4: repobrain costs ─────────────────────────────────────────────
def screenshot_costs() -> None:
    c = make_console()
    c.print()
    c.print(Panel.fit(
        "[bold cyan]repobrain[/] [white]costs --by operation[/]  —  [dim]All time[/]",
        border_style="bright_blue",
    ))
    c.print()

    t = Table(
        box=box.ROUNDED,
        border_style="bright_blue",
        header_style="bold cyan",
        show_lines=True,
        title="💰  LLM Spend by Operation",
    )
    t.add_column("Operation",      style="bold white")
    t.add_column("Calls",          justify="right")
    t.add_column("Input Tokens",   justify="right", style="dim")
    t.add_column("Output Tokens",  justify="right", style="dim")
    t.add_column("Cost (USD)",     justify="right")

    rows = [
        ("doc_generation",   "1,247", "5,612,000", "2,014,000", "[yellow]$9.84[/]"),
        ("explain_file",       "142",   "568,000",   "204,000",  "[green]$1.02[/]"),
        ("get_pr_impact",       "31",    "93,000",    "42,000",  "[green]$0.19[/]"),
        ("search_codebase",     "89",   "178,000",    "53,000",  "[green]$0.18[/]"),
        ("get_hotspots",        "47",    "94,000",    "28,000",  "[green]$0.09[/]"),
        ("get_knowledge_map",   "12",    "36,000",    "18,000",  "[green]$0.04[/]"),
    ]
    for row in rows:
        t.add_row(*row)

    t.add_section()
    t.add_row("[bold]TOTAL[/]", "[bold]1,568[/]", "[bold]6,581,000[/]", "[bold]2,359,000[/]", "[bold yellow]$11.36[/]")
    c.print(t)
    c.print()
    c.print("  [dim]Powered by[/] [bold cyan]tokenspy[/]  ·  Model: [bold]claude-sonnet-4-6[/]")
    c.print()
    c.save_svg(str(OUT / "screenshot-costs.svg"), title="repobrain costs")
    print("✓ screenshot-costs.svg")


# ── Screenshot 5: repobrain MCP tools in Claude Code ─────────────────────────
def screenshot_mcp() -> None:
    c = make_console()
    c.print()
    c.print(Panel(
        "[bold]repobrain MCP Server[/]  connected to Claude Code\n"
        "[dim]12 tools available[/dim]",
        border_style="bright_blue",
    ))
    c.print()

    t = Table(box=box.SIMPLE_HEAD, header_style="bold cyan", show_lines=False)
    t.add_column("Tool", style="bold cyan")
    t.add_column("Status", justify="center")
    t.add_column("Description", style="dim")

    tools = [
        ("explain_file",               "✓", "RAG-aware file documentation"),
        ("explain_symbol",             "✓", "Symbol-level explanation"),
        ("get_hotspots",               "✓", "Temporal decay hotspot ranking"),
        ("get_ownership",              "✓", "Temporal-weighted ownership"),
        ("get_dependencies",           "✓", "Import graph + dynamic hints"),
        ("get_architectural_decisions","✓", "ADR search and retrieval"),
        ("search_codebase",            "✓", "Semantic vector search"),
        ("get_cochange_patterns",      "✓", "Temporal co-change analysis"),
        ("get_pr_impact",              "★", "PR blast radius  [NEW]"),
        ("get_knowledge_map",          "★", "Knowledge silos & bus factor  [NEW]"),
        ("get_test_gaps",              "★", "Untested code by risk  [NEW]"),
        ("get_security_hotspots",      "★", "Auth/input/SQL surfaces  [NEW]"),
    ]
    for name, status, desc in tools:
        color = "green" if status == "✓" else "yellow"
        t.add_row(name, f"[{color}]{status}[/]", desc)

    c.print(t)
    c.print()
    c.save_svg(str(OUT / "screenshot-mcp-tools.svg"), title="repobrain MCP Tools")
    print("✓ screenshot-mcp-tools.svg")


if __name__ == "__main__":
    screenshot_index()
    screenshot_status()
    screenshot_review()
    screenshot_costs()
    screenshot_mcp()
    print(f"\nAll screenshots saved to {OUT}/")
