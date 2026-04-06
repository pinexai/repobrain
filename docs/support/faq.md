# FAQ

## General

### What languages does repobrain support?

Python, TypeScript, JavaScript, Go, Rust, Java. Additional languages fall back to regex-based import detection.

### Does repobrain send my code to Anthropic?

Yes — file content is sent to the Anthropic API for embedding and documentation generation. If this is a concern:

- Use `--no-docs` to skip doc generation entirely (no file content sent for generation, only for embeddings)
- Self-host a compatible embedding model and set `REPOMIND_EMBEDDING_MODEL`
- Review Anthropic's [data privacy policy](https://www.anthropic.com/privacy)

### How much does it cost to index a typical repo?

A 1,000-file Python repo with `claude-sonnet-4-6` for docs typically costs **$0.80–$1.50** for the initial full index. Incremental updates cost a fraction of that — only changed files are re-processed.

Use `--no-docs` to eliminate LLM costs entirely if you only want the graph + metrics.

### Can I use a different model?

Yes:
```bash
REPOMIND_LLM_MODEL=claude-haiku-4-5-20251001 repobrain index
```
Haiku is ~10× cheaper at some quality reduction. Opus gives best results at higher cost.

---

## Installation

### Does repobrain require Docker?

No. It runs entirely locally — SQLite, LanceDB, and NetworkX are all embedded. No external services required beyond the Anthropic API.

### Can I use repobrain offline?

Partially. The graph, metrics, and SQL data are local. MCP tools that don't require LLM calls (`get_hotspots`, `get_dependencies`, `get_cochange_patterns`) work offline. Anything requiring generation or embedding needs Anthropic API access.

### Does it work on Windows?

It runs on Windows via WSL2. Native Windows support is experimental.

---

## MCP & Claude Code

### How do I add repobrain to Claude Code?

```bash
repobrain serve --mcp-only
```

Then in Claude Code settings, add:
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

### Does repobrain work with other MCP clients?

Yes — it uses [fastmcp](https://github.com/jlowin/fastmcp) which is compatible with any MCP client (Claude Code, Claude Desktop, custom clients).

### How many repos can I index?

Each repo gets its own isolated data directory under `REPOMIND_DATA_DIR`. You can index as many repos as your disk allows. Switch between them:
```bash
repobrain serve --repo /path/to/repo-a
repobrain serve --repo /path/to/repo-b
```

---

## Webhooks

### What GitHub events does the webhook handle?

- `push` → incremental re-index of changed files
- `pull_request` (opened, synchronize, reopened) → blast radius analysis, comment posted to PR

### Does repobrain post comments to GitHub PRs?

Yes, when the webhook is configured and `GITHUB_TOKEN` is set. Comments include the blast radius table and risk score.

---

## Privacy & Security

### Is the PyPI token I used stored anywhere?

No. It was used only to upload the package and is not stored in any file.

### Can I restrict repobrain to only certain files?

Create a `.repobrain-ignore` file in your repo root (gitignore syntax):
```
secrets/
*.pem
.env*
```

### Does repobrain store credentials?

No credentials are stored by repobrain. The Anthropic API key is read from the environment at runtime.
