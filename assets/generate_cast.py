#!/usr/bin/env python3
"""Generate an asciinema v2 cast file for repobrain demo."""
from __future__ import annotations
import json
from pathlib import Path

WIDTH, HEIGHT = 120, 35
OUT = Path(__file__).parent / "demo.cast"

events: list[tuple[float, str, str]] = []
t = 0.0


def delay(seconds: float) -> None:
    global t
    t += seconds


def out(text: str, gap: float = 0.04) -> None:
    global t
    events.append((round(t, 4), "o", text))
    t += gap


def line(text: str = "", gap: float = 0.08) -> None:
    out(text + "\r\n", gap)


def slow_type(cmd: str) -> None:
    """Simulate human typing a command."""
    out("\r\n")
    out("\x1b[32m$\x1b[0m ")
    for ch in cmd:
        out(ch, 0.06)
    delay(0.4)
    out("\r\n", 0.1)


def prompt() -> None:
    out("\x1b[32m$\x1b[0m ", 0.05)


# ── Header ────────────────────────────────────────────────────────────────────
delay(0.5)
line("\x1b[1;36m╔══════════════════════════════════════════════════════╗\x1b[0m")
line("\x1b[1;36m║\x1b[0m  \x1b[1mrepobrain\x1b[0m — Codebase Intelligence That Thinks Ahead  \x1b[1;36m║\x1b[0m")
line("\x1b[1;36m╚══════════════════════════════════════════════════════╝\x1b[0m")
delay(0.8)

# ── Install ───────────────────────────────────────────────────────────────────
slow_type("pip install repobrain")
line("\x1b[2mCollecting repobrain\x1b[0m")
line("\x1b[2m  Downloading repobrain-0.1.1-py3-none-any.whl (91 kB)\x1b[0m")
out("\x1b[2m  \x1b[0m")
for i in range(1, 21):
    out(f"\x1b[2K\x1b[1G  \x1b[32m{'█' * i}{'░' * (20-i)}\x1b[0m {i*5:3d}%", 0.05)
line()
line("\x1b[32mSuccessfully installed repobrain-0.1.1\x1b[0m")
delay(0.5)

# ── Version ───────────────────────────────────────────────────────────────────
slow_type("repobrain --version")
line("\x1b[1mrepobrain\x1b[0m 0.1.1")
delay(0.6)

# ── Index ─────────────────────────────────────────────────────────────────────
slow_type("repobrain index ~/projects/myapp")
delay(0.3)
line("\x1b[1;36m◆\x1b[0m  Starting index: \x1b[1m~/projects/myapp\x1b[0m")
line()
stages = [
    ("Discovery",      "✓", "32", "Found \x1b[1m1,247\x1b[0m files in 3 languages"),
    ("Parse",          "✓", "32", "Parsed \x1b[1m1,247\x1b[0m files  (ProcessPoolExecutor × 8)"),
    ("Graph Build",    "✓", "32", "\x1b[1m14,382\x1b[0m nodes · \x1b[1m51,204\x1b[0m edges"),
    ("Git Analysis",   "✓", "32", "\x1b[1m8,420\x1b[0m commits · decay halflife 180 days"),
    ("Embedding",      "✓", "32", "\x1b[1m1,247\x1b[0m files embedded"),
    ("Doc Generation", "◉", "33", "Generating \x1b[1m623\x1b[0m/1,247 …"),
]
for stage, icon, color, detail in stages:
    line(f"  \x1b[{color}m{icon}\x1b[0m \x1b[1m{stage:<18}\x1b[0m {detail}", 0.3)

line()
bar = "=============================>          "
line(f"  \x1b[94m[\x1b[0m{bar}\x1b[94m]\x1b[0m \x1b[1m50%\x1b[0m  Stage: \x1b[33mGenerating Docs\x1b[0m  Files: \x1b[1m623/1,247\x1b[0m  Cost: \x1b[32m$0.41\x1b[0m  ETA: \x1b[2m2m 8s\x1b[0m")
delay(1.5)

line(f"  \x1b[94m[\x1b[0m{'=' * 40}\x1b[94m]\x1b[0m \x1b[1m100%\x1b[0m  Stage: \x1b[32mAtomic Commit\x1b[0m  Files: \x1b[1m1,247/1,247\x1b[0m  Cost: \x1b[32m$0.82\x1b[0m")
line()
line("\x1b[32m✓\x1b[0m  Index complete in \x1b[1m3m 41s\x1b[0m  ·  Cost: \x1b[1;32m$0.82\x1b[0m")
delay(0.8)

# ── Status ────────────────────────────────────────────────────────────────────
slow_type("repobrain status")
delay(0.2)
line("\x1b[1;36m┌─ Index Health ──────────────────────┐\x1b[0m")
line("\x1b[1;36m│\x1b[0m  SQLite   \x1b[32m✓\x1b[0m  1,247 records        \x1b[1;36m│\x1b[0m")
line("\x1b[1;36m│\x1b[0m  LanceDB  \x1b[32m✓\x1b[0m  1,247 vectors        \x1b[1;36m│\x1b[0m")
line("\x1b[1;36m│\x1b[0m  Graph    \x1b[32m✓\x1b[0m  14,382 nodes         \x1b[1;36m│\x1b[0m")
line("\x1b[1;36m│\x1b[0m  Status   \x1b[1;32mCONSISTENT\x1b[0m              \x1b[1;36m│\x1b[0m")
line("\x1b[1;36m└─────────────────────────────────────┘\x1b[0m")
line()
line("  \x1b[1m🔥 Top Hotspots\x1b[0m  (temporal decay · halflife 180d)")
line("  \x1b[2m──────────────────────────────────────────────────────\x1b[0m")
line("  \x1b[31m9.2\x1b[0m  src/auth/tokens.py         \x1b[2malice@co.com  99th\x1b[0m")
line("  \x1b[31m8.7\x1b[0m  src/api/endpoints.py       \x1b[2mbob@co.com    98th\x1b[0m")
line("  \x1b[33m7.4\x1b[0m  src/models/user.py         \x1b[2malice@co.com  94th\x1b[0m")
line("  \x1b[33m6.9\x1b[0m  src/billing/invoice.py     \x1b[2mcarol@co.com  91st\x1b[0m")
line("  \x1b[33m5.8\x1b[0m  src/notifications/email.py \x1b[2mbob@co.com    85th\x1b[0m")
delay(0.8)

# ── Review PR ─────────────────────────────────────────────────────────────────
slow_type("repobrain review 42")
delay(0.3)
line("\x1b[1;36m◆\x1b[0m  PR #42 — Add OAuth2 login flow")
line()
line("  \x1b[1mDirect Changes\x1b[0m (3 files)")
line("  \x1b[31m8.4\x1b[0m  src/auth/login.py    \x1b[32m✓ tests\x1b[0m   alice@co.com")
line("  \x1b[31m7.9\x1b[0m  src/auth/tokens.py   \x1b[31m✗ tests\x1b[0m   alice@co.com")
line("  \x1b[33m6.1\x1b[0m  src/models/user.py   \x1b[32m✓ tests\x1b[0m   bob@co.com")
line()
line("  \x1b[1mTransitive Dependents\x1b[0m (8 files)")
line("  \x1b[33m5.3\x1b[0m  src/api/endpoints.py      \x1b[2mvia src/auth/login.py\x1b[0m")
line("  \x1b[33m4.8\x1b[0m  src/middleware/auth.py     \x1b[2mvia src/auth/tokens.py\x1b[0m")
line("  \x1b[32m2.1\x1b[0m  src/tests/test_login.py   \x1b[2mvia src/auth/login.py\x1b[0m")
line("  \x1b[2m+ 5 more …\x1b[0m")
line()
line("\x1b[33m⚠\x1b[0m  Co-change: \x1b[1msrc/auth/middleware.py\x1b[0m missing (78% co-change with login.py)")
line()
line("  Reviewers: \x1b[36malice@co.com\x1b[0m · \x1b[36mbob@co.com\x1b[0m")
line()
line("\x1b[1;31m  Overall Risk: 7.8 / 10.0  [HIGH]\x1b[0m")
delay(0.8)

# ── Costs ─────────────────────────────────────────────────────────────────────
slow_type("repobrain costs --by operation")
delay(0.2)
line("  \x1b[1mLLM Spend by Operation\x1b[0m")
line("  \x1b[2m───────────────────────────────────────────────────\x1b[0m")
line("  doc_generation    1,247 calls   \x1b[33m$9.84\x1b[0m")
line("  explain_file        142 calls   \x1b[32m$1.02\x1b[0m")
line("  get_pr_impact        31 calls   \x1b[32m$0.19\x1b[0m")
line("  search_codebase      89 calls   \x1b[32m$0.18\x1b[0m")
line("  \x1b[2m───────────────────────────────────────────────────\x1b[0m")
line("  \x1b[1mTOTAL             1,568 calls   \x1b[1;33m$11.36\x1b[0m")
line()
line("  \x1b[2mPowered by tokenspy  ·  Model: claude-sonnet-4-6\x1b[0m")
delay(1.0)

# ── Footer ────────────────────────────────────────────────────────────────────
line()
line("\x1b[1;36m──────────────────────────────────────────────────────\x1b[0m")
line("  Add to Claude Code:  \x1b[1mrepobrain serve --mcp-only\x1b[0m")
line("  PyPI:  \x1b[36mpip install repobrain\x1b[0m")
line("  Docs:  \x1b[36mhttps://pinexai.github.io/repobrain\x1b[0m")
line("\x1b[1;36m──────────────────────────────────────────────────────\x1b[0m")
delay(0.5)
prompt()

# ── Write cast file ───────────────────────────────────────────────────────────
header = {
    "version": 2,
    "width": WIDTH,
    "height": HEIGHT,
    "timestamp": 1743897600,
    "title": "repobrain — Codebase Intelligence Demo",
    "env": {"TERM": "xterm-256color", "SHELL": "/bin/zsh"},
}

with open(OUT, "w") as f:
    f.write(json.dumps(header) + "\n")
    for ts, typ, data in events:
        f.write(json.dumps([ts, typ, data]) + "\n")

print(f"✓ demo.cast written ({len(events)} events, {t:.1f}s total)")
