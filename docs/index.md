# repobrain

**Codebase intelligence that thinks ahead.**

repobrain is an MCP server for Claude that gives it deep, always-fresh understanding of your codebase — with 10× faster indexing, RAG-aware documentation, PR blast radius analysis, and temporal hotspot scoring.

## Why repobrain?

After analyzing repowise (the previous best-in-class codebase intelligence MCP server) in depth, we found **10 critical architectural flaws**. repobrain fixes every one:

| # | Repowise Flaw | repobrain Fix |
|---|---------------|--------------|
| 1 | RAG context never used during generation | `RAGAwareDocGenerator` fetches dep docs from LanceDB *before* every LLM call |
| 2 | 25+ min initial indexing | 7-stage async pipeline with `ProcessPoolExecutor` + concurrent git/parse |
| 3 | No atomic transactions across 3 stores | `AtomicStorageCoordinator` rolls back SQL + LanceDB + NetworkX atomically |
| 4 | Hardcoded 500-commit limit | Configurable `GitConfig.max_commits = 10_000` |
| 5 | Dynamic imports invisible (20–40% missing edges) | Django, pytest, Node hint extractors |
| 6 | Incremental updates miss percentile recalculation | `upsert()` always triggers `PERCENT_RANK()` window refresh |
| 7 | No PR blast radius analysis | `PRBlastRadiusAnalyzer` + `get_pr_impact` MCP tool |
| 8 | Temporal blindness (old commits = recent commits) | Exponential decay scoring |
| 9 | Zero cost visibility | `TokenspyCostAdapter` + `repobrain costs` CLI |
| 10 | Conservative dead code detection | Dynamic hint edge recovery |

## New Capabilities (not in repowise)

- **`get_pr_impact`** — full blast radius before merge: direct + transitive files, risk score 0–10, co-change warnings, reviewer recommendations
- **`get_knowledge_map`** — knowledge silos, bus factor, onboarding targets
- **`get_test_gaps`** — untested code ranked by risk score
- **`get_security_hotspots`** — auth/input/SQL risk surfaces

## Get Started

```bash
pip install repobrain
repobrain index /path/to/your/repo
repobrain serve  # start MCP server
```

See the [Quick Start guide](getting-started/quickstart.md) for full setup.
