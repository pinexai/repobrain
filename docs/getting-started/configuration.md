# Configuration

All configuration is via environment variables or a `.env` file in your working directory.

## Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `REPOMIND_DATA_DIR` | `~/.repobrain` | Where repobrain stores indexes |
| `REPOMIND_LOG_LEVEL` | `INFO` | Logging level |

## Git Analysis

| Variable | Default | Description |
|----------|---------|-------------|
| `REPOMIND_MAX_COMMITS` | `10000` | Maximum commits to analyze |
| `REPOMIND_DECAY_HALFLIFE_DAYS` | `180` | Halflife for temporal decay scoring |

## Generation

| Variable | Default | Description |
|----------|---------|-------------|
| `REPOMIND_LLM_MODEL` | `claude-sonnet-4-6` | Model for doc generation |
| `REPOMIND_GENERATION_CONCURRENCY` | `5` | Max concurrent generation calls |

## Servers

| Variable | Default | Description |
|----------|---------|-------------|
| `REPOMIND_MCP_PORT` | `8766` | MCP server port |
| `REPOMIND_WEBHOOK_PORT` | `8765` | GitHub webhook port |
| `REPOMIND_WEBHOOK_SECRET` | *(optional)* | GitHub webhook HMAC secret |

## Example `.env`

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
REPOMIND_DATA_DIR=~/.repobrain
REPOMIND_MAX_COMMITS=10000
REPOMIND_DECAY_HALFLIFE_DAYS=180
REPOMIND_GENERATION_CONCURRENCY=5
REPOMIND_MCP_PORT=8766
REPOMIND_WEBHOOK_PORT=8765
REPOMIND_WEBHOOK_SECRET=your-github-webhook-secret
```
