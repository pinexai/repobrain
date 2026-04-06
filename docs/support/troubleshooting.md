# Troubleshooting

## Indexing Issues

### Index hangs on "Doc Generation"

**Symptom:** Progress bar stalls at Stage 6, no forward movement for >5 minutes.

**Causes & Fixes:**

1. **Anthropic rate limit** — reduce concurrency:
   ```bash
   REPOMIND_GENERATION_CONCURRENCY=2 repobrain index --incremental
   ```

2. **API key invalid or quota exhausted** — verify:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
   ```

3. **Use `--no-docs` to skip generation entirely:**
   ```bash
   repobrain index --no-docs  # skips Stage 6, much faster
   ```

---

### `ModuleNotFoundError` on startup

```
ModuleNotFoundError: No module named 'lancedb'
```

Ensure you installed into the correct Python environment:
```bash
pip install repobrain
python -c "import lancedb; print('ok')"
```

If using a virtual environment, activate it first:
```bash
source .venv/bin/activate
pip install repobrain
```

---

### "Index inconsistent" in `repobrain status`

**Symptom:**
```
Consistent: ✗ NO  (SQL: 500, Graph: 498, Vector: 501)
```

**Fix:** Re-index from scratch:
```bash
rm -rf ~/.repomind/<repo-id>/
repobrain index /path/to/repo --full
```

To find the repo ID:
```bash
repobrain status --show-id
```

---

### Tree-sitter parse errors for some files

Some files may fail to parse (unsupported language or syntax error). repobrain falls back to regex parsing for these. Check logs:
```bash
REPOMIND_LOG_LEVEL=DEBUG repobrain index 2>&1 | grep "parse error"
```

---

## PR Review Issues

### `repobrain review` returns empty transitive list

**Cause:** Graph was built without those files (filtered by language or failed to parse).

**Fix:** Re-index with verbose logging to check coverage:
```bash
REPOMIND_LOG_LEVEL=DEBUG repobrain index --incremental 2>&1 | grep -E "skip|error"
```

### PR number not found

`repobrain review` requires a GitHub remote. Ensure your repo has a remote named `origin`:
```bash
git remote -v
# origin  https://github.com/org/repo.git (fetch)
```

---

## Webhook Issues

### 400 responses from webhook endpoint

Almost always an HMAC signature mismatch. Verify:
1. `REPOMIND_WEBHOOK_SECRET` matches the secret configured in GitHub Settings → Webhooks
2. GitHub is sending `Content-Type: application/json` (not `application/x-www-form-urlencoded`)

Test locally with:
```bash
repobrain serve --debug
```

---

## Performance Issues

### Indexing takes >10 minutes for a 500-file repo

Default concurrency may be too low. Tune:
```bash
REPOMIND_GENERATION_CONCURRENCY=10 repobrain index
```

For repos with very large files (>500 KB), embedding may be slow. Skip large files:
```bash
# Add to .repobrain-ignore (gitignore syntax)
*.min.js
vendor/
node_modules/
```

---

## Getting Help

- GitHub Issues: [github.com/pinexai/repobrain/issues](https://github.com/pinexai/repobrain/issues)
- Enable debug logs: `REPOMIND_LOG_LEVEL=DEBUG repobrain <command> 2>&1 | tee repobrain-debug.log`
- Include the debug log when filing issues
