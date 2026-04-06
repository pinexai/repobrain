# Production Deployment

## Recommended Architecture

```
GitHub Webhook ──► repobrain webhook server (port 8765)
                        │
                        ▼
                  Auto-index on push
                  Blast radius on PR ──► GitHub PR comment
                        │
                        ▼
Claude Code ◄──── repobrain MCP server (port 8766)
```

## systemd Service

Create `/etc/systemd/system/repobrain.service`:

```ini
[Unit]
Description=repobrain MCP + webhook server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=repobrain
WorkingDirectory=/opt/repobrain
EnvironmentFile=/etc/repobrain/env
ExecStartPre=/usr/local/bin/repobrain index /opt/repos/myapp --incremental --no-docs
ExecStart=/usr/local/bin/repobrain serve
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=repobrain

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/repobrain

[Install]
WantedBy=multi-user.target
```

`/etc/repobrain/env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...
REPOMIND_DATA_DIR=/var/lib/repobrain
REPOMIND_WEBHOOK_SECRET=your-github-webhook-secret
REPOMIND_MCP_PORT=8766
REPOMIND_WEBHOOK_PORT=8765
REPOMIND_MAX_COMMITS=10000
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable repobrain
sudo systemctl start repobrain
sudo journalctl -u repobrain -f
```

---

## Reverse Proxy (nginx)

Expose the webhook publicly while keeping the MCP server internal:

```nginx
server {
    listen 443 ssl;
    server_name repobrain.yourcompany.com;

    # SSL config here ...

    # Webhook — public
    location /webhook {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # MCP — restrict to internal IPs only
    location / {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        deny all;
        proxy_pass http://127.0.0.1:8766;
    }
}
```

---

## Monitoring

### Log format

repobrain emits structured JSON logs at `INFO` level by default:

```json
{"event": "index_complete", "repo": "myapp", "files": 1247, "duration_s": 221, "cost_usd": 0.82, "timestamp": "2026-04-06T10:00:00Z"}
{"event": "pr_analyzed", "pr": 42, "risk_score": 7.8, "direct_files": 3, "transitive_files": 8, "timestamp": "2026-04-06T10:05:00Z"}
```

Ship to your SIEM/log aggregator via `journald` or stdout.

### Key metrics to alert on

| Metric | Warning | Critical |
|--------|---------|----------|
| Index duration | >10 min | >30 min |
| Consistency check | inconsistent | — |
| LLM daily cost | >$5 | >$20 |
| Webhook 4xx rate | >5% | >20% |

---

## Backup

repobrain's data is in `REPOMIND_DATA_DIR` (default `~/.repomind`). Back up this directory. The index can always be rebuilt with `repobrain index --full`, but backups avoid the LLM cost of regeneration.

```bash
# Daily backup
tar -czf repobrain-backup-$(date +%Y%m%d).tar.gz ~/.repomind/
```
