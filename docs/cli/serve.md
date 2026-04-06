# repobrain serve

Start the MCP server and optionally the GitHub webhook server.

## Usage

```bash
repobrain serve [OPTIONS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--mcp-port N` | `8766` | MCP server port |
| `--webhook-port N` | `8765` | Webhook server port |
| `--mcp-only` | — | Start MCP server only (no webhook) |
| `--repo PATH` | `.` | Repository to serve |

## Claude Code Integration

Add to `~/.claude.json` or your project's MCP config:

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

## GitHub Webhook Setup

1. In your GitHub repo: Settings → Webhooks → Add webhook
2. Payload URL: `https://your-server:8765/webhook`
3. Content type: `application/json`
4. Secret: same as `REPOMIND_WEBHOOK_SECRET` in `.env`
5. Events: Push, Pull requests

repobrain will automatically:
- Re-index changed files on `push` events
- Run blast radius analysis on `pull_request` open/sync events
