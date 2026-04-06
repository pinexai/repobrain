# Docker Deployment

Run repobrain as a persistent MCP + webhook server in Docker.

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install git (required for GitPython)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install repobrain
RUN pip install repobrain

# Persist data between container restarts
VOLUME ["/data"]

EXPOSE 8766 8765

ENV REPOMIND_DATA_DIR=/data

CMD ["repobrain", "serve", "--mcp-port", "8766", "--webhook-port", "8765"]
```

## docker-compose.yml

```yaml
version: "3.9"

services:
  repobrain:
    build: .
    restart: unless-stopped
    ports:
      - "8766:8766"   # MCP
      - "8765:8765"   # Webhook
    volumes:
      - repobrain-data:/data
      - ${REPO_PATH}:/repo:ro   # mount your repo read-only
    environment:
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      REPOMIND_DATA_DIR: /data
      REPOMIND_WEBHOOK_SECRET: ${REPOMIND_WEBHOOK_SECRET}
      REPOMIND_MAX_COMMITS: 10000
    command: >
      sh -c "repobrain index /repo --no-docs && repobrain serve"

volumes:
  repobrain-data:
```

## Running

```bash
REPO_PATH=/path/to/your/repo \
ANTHROPIC_API_KEY=sk-ant-... \
REPOMIND_WEBHOOK_SECRET=your-secret \
docker compose up -d
```

Check logs:
```bash
docker compose logs -f repobrain
```

---

## Health Check

Add to your compose file for orchestration:

```yaml
healthcheck:
  test: ["CMD", "repobrain", "status", "--json"]
  interval: 60s
  timeout: 10s
  retries: 3
```
