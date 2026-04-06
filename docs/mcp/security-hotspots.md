# get_security_hotspots

Find high-risk security surfaces: authentication code, user input handling, SQL operations, and other OWASP-relevant patterns.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `severity` | str | `"medium"` | Minimum severity: `"low"`, `"medium"`, `"high"`, `"critical"` |
| `pattern_set` | list | all | Filter to: `"auth"`, `"input"`, `"sql"`, `"crypto"`, `"file_io"` |
| `file_path` | str | `null` | Limit to a specific file |

## Response

```json
{
  "hotspots": [
    {
      "file_path": "src/auth/login.py",
      "pattern": "auth",
      "severity": "high",
      "symbols": ["verify_password", "create_session"],
      "risk_score": 8.4,
      "reason": "Authentication logic in high-churn file with bus factor 1"
    },
    {
      "file_path": "src/api/search.py",
      "pattern": "input",
      "severity": "medium",
      "symbols": ["search_handler"],
      "risk_score": 5.2,
      "reason": "User input handler with no test coverage"
    }
  ]
}
```

## Pattern Detection

Patterns are detected by combining:
- Symbol name heuristics (`login`, `password`, `token`, `execute`, `query`, etc.)
- Import analysis (`hashlib`, `sqlite3`, `subprocess`, etc.)
- Hotspot score (high-churn risky code = higher priority)
