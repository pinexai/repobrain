#!/usr/bin/env bash
# repomind demo recording script
# Usage:
#   asciinema rec docs/assets/demo.cast --title "repomind demo" --idle-time-limit 2
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
echo "  repomind — Codebase Intelligence That Thinks Ahead"
echo "============================================================"
echo ""
sleep 1

# ── Install ───────────────────────────────────────────────────
type_cmd "pip install repomind"
sleep 0.5

# ── Configure ────────────────────────────────────────────────
type_cmd "repomind --version"
sleep 0.5

# ── Index ────────────────────────────────────────────────────
echo ""
echo "# Index a real repository"
type_cmd "repomind index $DEMO_REPO --no-docs --max-commits 100"

# ── Status ───────────────────────────────────────────────────
echo ""
echo "# Check status and hotspots"
type_cmd "repomind status"

# ── Review a PR ──────────────────────────────────────────────
echo ""
echo "# Analyze PR blast radius"
type_cmd "repomind review 1 --format table"

# ── Costs ────────────────────────────────────────────────────
echo ""
echo "# Check LLM spend"
type_cmd "repomind costs --by operation"

echo ""
echo "============================================================"
echo "  Done! Add repomind to Claude Code:"
echo "  repomind serve --mcp-only"
echo "============================================================"
