# get_test_gaps

Find untested code, ranked by risk score so you know where to write tests first.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | str | `null` | Limit to a specific file |
| `min_complexity_threshold` | float | `0.5` | Minimum complexity to include |
| `top_n` | int | `20` | Maximum results to return |

## Response

```json
{
  "test_gaps": [
    {
      "file_path": "src/auth/tokens.py",
      "symbols_untested": ["generate_token", "validate_token"],
      "risk_score": 8.1,
      "hotspot_score": 6.3,
      "centrality": 0.65,
      "suggested_test_file": "tests/unit/test_tokens.py"
    }
  ],
  "coverage_estimate": 0.43,
  "total_symbols": 312,
  "untested_symbols": 178
}
```

## How Test Gaps Are Detected

1. Parse all test files to extract which symbols are referenced
2. Compare against all defined symbols in source files
3. Symbols not referenced in any test file = potential test gap
4. Rank by `risk_score = hotspot_score × centrality`
