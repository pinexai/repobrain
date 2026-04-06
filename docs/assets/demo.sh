#!/usr/bin/env bash
# repobrain demo recording script
# Usage:
#   asciinema rec docs/assets/demo.cast --title "repobrain demo" --idle-time-limit 2
#   Then run this script interactively, or pipe it:
#   asciinema rec docs/assets/demo.cast -c "bash docs/assets/demo.sh"

set -e

DEMO_REPO="${1:-/tmp/demo-repo}"

# Helper: type text with delay (simulates human typing)
type_cmd() {
    echo -n "$ "
    echo "$1" | pv -qL 30
    sleep 0.5
    eval "$1"
    sleep 1
}

echo ""
echo "============================================================"
echo "  repobrain — Codebase Intelligence That Thinks Ahead"
echo "============================================================"
echo ""
sleep 1

# ── Install ───────────────────────────────────────────────────
type_cmd "pip install repobrain"
sleep 0.5

# ── Configure ────────────────────────────────────────────────
type_cmd "repobrain --version"
sleep 0.5

# ── Index ────────────────────────────────────────────────────
echo ""
echo "# Index a real repository"
type_cmd "repobrain index $DEMO_REPO --no-docs --max-commits 100"

# ── Status ───────────────────────────────────────────────────
echo ""
echo "# Check status and hotspots"
type_cmd "repobrain status"

# ── Review a PR ──────────────────────────────────────────────
echo ""
echo "# Analyze PR blast radius"
type_cmd "repobrain review 1 --format table"

# ── Costs ────────────────────────────────────────────────────
echo ""
echo "# Check LLM spend"
type_cmd "repobrain costs --by operation"

echo ""
echo "============================================================"
echo "  Done! Add repobrain to Claude Code:"
echo "  repobrain serve --mcp-only"
echo "============================================================"
