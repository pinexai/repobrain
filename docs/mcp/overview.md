# MCP Tools Overview

repobrain exposes 12 MCP tools to Claude. 8 improve on repowise's tools; 4 are entirely new.

## All Tools

| Tool | New? | Description |
|------|------|-------------|
| `explain_file` | — | File documentation with RAG-injected dependency context |
| `explain_symbol` | — | Symbol-level explanation (class, function, variable) |
| `get_hotspots` | — | Temporal decay–weighted churn hotspots |
| `get_ownership` | — | Temporal-weighted file ownership by contributor |
| `get_dependencies` | — | Import graph with dynamic hint edges included |
| `get_architectural_decisions` | — | ADR search and retrieval |
| `search_codebase` | — | Semantic vector search across all files |
| `get_cochange_patterns` | — | Temporal co-change analysis between files |
| [`get_pr_impact`](pr-impact.md) | **NEW** | Full blast radius for a PR |
| [`get_knowledge_map`](knowledge-map.md) | **NEW** | Knowledge silos, bus factor, onboarding targets |
| [`get_test_gaps`](test-gaps.md) | **NEW** | Untested code ranked by risk score |
| [`get_security_hotspots`](security-hotspots.md) | **NEW** | Auth/input/SQL risk surfaces |

## Key Improvements Over repowise

### RAG-Aware Documentation

Every `explain_file` call now fetches existing documentation for all dependency files from LanceDB *before* calling the LLM. This means:
- Generated docs reference what dependencies actually do
- Cross-file relationships are accurately described
- No more context-free docs that ignore imports

### Temporal Hotspots

`get_hotspots` uses exponential decay scoring: files changed frequently *recently* rank higher than files with high historical churn but no recent activity.

### Dynamic Import Edges

`get_dependencies` includes edges discovered by:
- `DjangoDynamicHints` — INSTALLED_APPS, ROOT_URLCONF, middleware
- `PytestDynamicHints` — conftest.py fixture usage
- `NodeDynamicHints` — package.json `main`, webpack aliases
