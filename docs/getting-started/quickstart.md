# Quick Start

## 1. Configure

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

## 2. Index your repository

```bash
repobrain index /path/to/your/repo
```

You'll see a Rich progress bar:

```
[=====>     ] 47% | Stage: Generating Docs | Files: 234/500 | Cost: $0.23 | ETA: 4m12s
```

For large repos, use incremental mode on subsequent runs:

```bash
repobrain index /path/to/your/repo --incremental
```

## 3. Check status

```bash
repobrain status
```

Shows hotspot rankings, index health, and consistency check across all three stores.

## 4. Review a PR

```bash
repobrain review 42
```

Output includes:
- Direct files changed
- Transitive dependents (files that import changed files)
- Risk score 0–10
- Co-change warnings (files historically changed together but missing from PR)
- Recommended reviewers

## 5. Start MCP server

```bash
repobrain serve
```

Then add repobrain to your Claude Code MCP configuration:

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

Now Claude Code has access to all 12 repobrain tools.

## 6. Query your codebase

```bash
repobrain query "where is authentication handled?"
```

## 7. Track LLM costs

```bash
repobrain costs
repobrain costs --since 2026-01-01 --by operation
```
