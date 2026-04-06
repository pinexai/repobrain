# get_pr_impact

Analyze the blast radius of a pull request — which files are directly changed, which are transitively affected, and what the overall risk is.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pr_number` | int | *(required)* | GitHub PR number |
| `include_transitive` | bool | `true` | Include transitive dependents |
| `max_depth` | int | `3` | Traversal depth for transitive dependencies |

## Response

```json
{
  "pr_number": 42,
  "changed_files": [
    {
      "file_path": "src/auth/login.py",
      "risk_score": 8.2,
      "centrality": 0.71,
      "hotspot_score": 6.3,
      "owner_email": "alice@co.com",
      "test_gap": false
    }
  ],
  "transitive_files": [...],
  "cochange_warnings": [
    {
      "missing_file": "src/auth/middleware.py",
      "related_to": "src/auth/login.py",
      "cochange_score": 0.72,
      "message": "Historically changed together 72% of the time"
    }
  ],
  "recommended_reviewers": ["alice@co.com", "bob@co.com"],
  "test_gap_files": ["src/auth/tokens.py"],
  "overall_risk_score": 7.8,
  "analyzed_at": "2026-04-06T12:00:00Z"
}
```

## Risk Score Formula

```python
risk = centrality × temporal_hotspot_score × (1 + test_gap_penalty)
# normalized to 0-10 across the repository
```

## Example Claude Code Usage

In Claude Code with repomind as an MCP server:

```
Use get_pr_impact for PR #42 and summarize the risk
```

Claude will return a natural language summary of:
- Which files are most at risk
- Which reviewers to assign
- Whether any co-change partners are missing
