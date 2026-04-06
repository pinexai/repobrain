# get_knowledge_map

Identify knowledge silos, bus factor, and onboarding targets in your codebase.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scope` | str | `"repo"` | `"repo"`, `"module"`, or `"author"` |
| `module_path` | str | `null` | Filter to a specific module path |
| `author_email` | str | `null` | Focus on a specific contributor |

## Use Cases

- **Pre-hire**: "Which parts of the codebase does only one person understand?"
- **Offboarding**: "Bob is leaving — what does only he know?"
- **Onboarding**: "What should a new engineer learn first?"

## Response

```json
{
  "knowledge_silos": [
    {
      "path": "src/billing/",
      "bus_factor": 1,
      "sole_owner": "alice@co.com",
      "risk": "critical"
    }
  ],
  "bus_factor_by_module": {
    "src/auth/": 2,
    "src/billing/": 1,
    "src/api/": 4
  },
  "onboarding_sequence": [
    "src/models/user.py",
    "src/api/endpoints.py",
    "src/auth/login.py"
  ],
  "contributor_coverage": {
    "alice@co.com": ["src/auth/", "src/billing/"],
    "bob@co.com": ["src/api/", "src/models/"]
  }
}
```
