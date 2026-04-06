# Migrating from repowise

repobrain is a drop-in replacement for repowise. Migration takes under 5 minutes.

## Step 1 — Install repobrain

```bash
pip install repobrain
```

You can keep repowise installed — they don't conflict.

## Step 2 — Index your repository

```bash
repobrain index /path/to/your/repo
```

repobrain builds its own index (separate from repowise's). The first run takes 3–5 minutes for a 1,000-file repo.

## Step 3 — Update your MCP config

**Before (repowise):**
```json
{
  "mcpServers": {
    "repowise": {
      "command": "repowise",
      "args": ["serve"]
    }
  }
}
```

**After (repobrain):**
```json
{
  "mcpServers": {
    "repobrain": {
      "command": "repobrain",
      "args": ["serve", "--mcp-only"]
    }
  }
}
```

## Step 4 — Verify tools are available

In Claude Code, type:
```
List available MCP tools
```

You should see all 12 repobrain tools.

---

## Tool Name Mapping

All repowise tool names work in repobrain. The 4 new tools are additive.

| repowise tool | repobrain equivalent | Improvements |
|---------------|----------------------|--------------|
| `explain_file` | `explain_file` | RAG-injected dependency context |
| `explain_symbol` | `explain_symbol` | Same |
| `get_hotspots` | `get_hotspots` | Temporal decay scoring |
| `get_ownership` | `get_ownership` | Temporal-weighted |
| `get_dependencies` | `get_dependencies` | Dynamic import edges |
| `get_architectural_decisions` | `get_architectural_decisions` | Same |
| `search_codebase` | `search_codebase` | Same |
| `get_cochange_patterns` | `get_cochange_patterns` | Temporal-weighted |
| *(not in repowise)* | `get_pr_impact` | **NEW** |
| *(not in repowise)* | `get_knowledge_map` | **NEW** |
| *(not in repowise)* | `get_test_gaps` | **NEW** |
| *(not in repowise)* | `get_security_hotspots` | **NEW** |

---

## Environment Variable Mapping

| repowise | repobrain | Notes |
|----------|-----------|-------|
| `ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` | Same |
| `REPOWISE_MAX_COMMITS` | `REPOMIND_MAX_COMMITS` | Default raised to 10,000 |
| `REPOWISE_DATA_DIR` | `REPOMIND_DATA_DIR` | New location |
| *(none)* | `REPOMIND_DECAY_HALFLIFE_DAYS` | New: temporal decay |
| *(none)* | `REPOMIND_GENERATION_CONCURRENCY` | New: parallel generation |

---

## Can I keep using repowise?

Yes. repobrain does not modify or delete repowise's data. Run both in parallel while evaluating.

## Can I delete repowise's data after migrating?

```bash
rm -rf ~/.repowise/   # default repowise data dir
```

Only do this after confirming repobrain is working correctly.
