<div align="center">
  <img src="docs/assets/logo.svg" width="100" alt="repobrain logo" />
  <h1>repobrain</h1>
  <p><strong>Codebase intelligence that thinks ahead.</strong></p>

  [![PyPI version](https://img.shields.io/pypi/v/repobrain.svg?style=flat-square)](https://pypi.org/project/repobrain/)
  [![Downloads](https://img.shields.io/pypi/dm/repobrain.svg?style=flat-square)](https://pypi.org/project/repobrain/)
  [![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](https://www.python.org/downloads/)
  [![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
  [![CI](https://img.shields.io/github/actions/workflow/status/pinexai/repobrain/ci.yml?style=flat-square&label=CI)](https://github.com/pinexai/repobrain/actions/workflows/ci.yml)
  [![MCP Compatible](https://img.shields.io/badge/MCP-compatible-blueviolet?style=flat-square)](https://modelcontextprotocol.io)
  [![Docs](https://img.shields.io/badge/docs-pinexai.github.io-blue?style=flat-square)](https://pinexai.github.io/repobrain)
  [![GitHub Stars](https://img.shields.io/github/stars/pinexai/repobrain?style=flat-square&logo=github)](https://github.com/pinexai/repobrain)
</div>

---

> **repobrain** is a self-hosted MCP server for Claude that gives it deep, always-fresh understanding of your codebase — 10× faster indexing, RAG-aware documentation, PR blast radius, temporal hotspot scoring, and 12 MCP tools.
>
> It fixes every critical architectural flaw in repowise, then goes further.

---

## Four Intelligence Layers

| 🔗 Graph Intelligence | ⏱ Temporal Intelligence |
|---|---|
| tree-sitter + NetworkX dependency graph with PageRank centrality. Dynamic import hints for Django, pytest, and Node recover **20–40% missing edges** that repowise silently drops. | Exponential decay scoring weights recent commits exponentially higher. A commit from yesterday matters far more than one from 2 years ago. Configurable half-life. |

| 📚 Documentation Intelligence | 💥 PR Intelligence |
|---|---|
| `RAGAwareDocGenerator` fetches dependency docs from LanceDB **before** every LLM call — not after. This is the #1 architectural difference from repowise. | `PRBlastRadiusAnalyzer` traces direct + transitive impact of every PR, scores risk 0–10, flags co-change pairs, and recommends reviewers. |

---

## Why repobrain Beats Repowise

| # | Repowise Flaw | repobrain Fix |
|---|---|---|
| 1 | **RAG context never used during generation** — vector store populated but never queried | `RAGAwareDocGenerator` fetches dependency docs from LanceDB *before* every LLM call |
| 2 | **25+ min initial indexing** — no parallelism | 7-stage async pipeline; parse in `ProcessPoolExecutor`, git + graph run concurrently |
| 3 | **3 stores, no atomic transactions** — 5–15% silent consistency failures | `AtomicStorageCoordinator` buffers + rolls back SQL, LanceDB, and NetworkX atomically |
| 4 | **Hardcoded 500-commit limit** | `GitConfig.max_commits = 10_000` — fully configurable |
| 5 | **Dynamic imports invisible** (Django, pytest, importlib) — 20–40% missing graph edges | `DjangoDynamicHints`, `PytestDynamicHints`, `NodeDynamicHints` in `HintRegistry` |
| 6 | **Incremental updates miss global percentile recalculation** | `upsert()` always triggers `PERCENT_RANK()` window function refresh |
| 7 | **No PR blast radius analysis** | `PRBlastRadiusAnalyzer` + `repobrain review <PR>` + `get_pr_impact` MCP tool |
| 8 | **Temporal blindness** — 3-year-old commits weighted same as yesterday's | Exponential decay: `score += exp(-ln(2) × age_days / halflife) × complexity` |
| 9 | **Zero cost visibility** | `TokenspyCostAdapter` wraps every Anthropic call; `repobrain costs` CLI |
| 10 | **Conservative dead code** misses real candidates | Dynamic hint edges recovered; configurable sensitivity threshold |

**[Full comparison →](https://pinexai.github.io/repobrain/comparison/)**

---

## What's New (Not in Repowise)

| Tool | Description |
|---|---|
| `get_pr_impact` | Full blast radius before merge: direct + transitive files, risk score 0–10, co-change warnings, reviewer recommendations |
| `get_knowledge_map` | Knowledge silos, bus factor per module, onboarding targets for new engineers |
| `get_test_gaps` | Untested code ranked by combined risk score (hotspot × centrality) |
| `get_security_hotspots` | Auth handlers, input validation points, SQL surfaces — ranked by exposure |

---

## Installation

```bash
pip install repobrain
```

**Requirements:** Python 3.12+, Anthropic API key.

---

## Quick Start

```bash
# 1. Configure
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Index your repository (3–5 min for 1,000 files)
repobrain index /path/to/your/repo

# 3. Analyze a PR before merging
repobrain review 42

# 4. Start MCP server for Claude Code
repobrain serve
```

**Add to your Claude Code MCP config:**

```json
{
  "mcpServers": {
    "repobrain": {
      "command": "repobrain",
      "args": ["serve", "--mcp-only"]
    }
  }
}
```

---

## CLI Commands

| Command | Description |
|---|---|
| `repobrain index [PATH]` | Index a repository (full or incremental) |
| `repobrain review <PR>` | PR blast radius: risk score, affected files, reviewer recommendations |
| `repobrain serve` | Start MCP server (+ optional GitHub webhook) |
| `repobrain status` | Temporal hotspot rankings and index health |
| `repobrain query "<text>"` | Natural language codebase search |
| `repobrain costs [--since DATE]` | Per-operation LLM spend breakdown |

**Rich progress during indexing:**
```
[=====>     ] 47% │ Stage: Generating Docs │ Files: 234/500 │ Cost: $0.23 │ ETA: 4m 12s
```

---

## MCP Tools (12 total)

| Tool | Status | Description |
|---|---|---|
| `explain_file` | — | File docs with RAG-injected dependency context |
| `explain_symbol` | — | Symbol-level explanation |
| `get_hotspots` | — | Temporal decay–weighted churn hotspots |
| `get_ownership` | — | Temporal-weighted file ownership |
| `get_dependencies` | — | Import graph with dynamic hint edges |
| `get_architectural_decisions` | — | ADR search and retrieval |
| `search_codebase` | — | Semantic vector search |
| `get_cochange_patterns` | — | Temporal co-change analysis |
| `get_pr_impact` | **NEW** | Full blast radius for a PR |
| `get_knowledge_map` | **NEW** | Knowledge silos, bus factor, onboarding targets |
| `get_test_gaps` | **NEW** | Untested code ranked by risk score |
| `get_security_hotspots` | **NEW** | Auth/input/SQL risk surfaces |

---

## Language Support

| Language | Parsing | Graph | Dynamic Hints |
|---|---|---|---|
| Python | ✅ tree-sitter | ✅ imports + calls | ✅ Django, pytest, importlib |
| TypeScript | ✅ tree-sitter | ✅ imports + re-exports | — |
| JavaScript | ✅ tree-sitter | ✅ require + import | ✅ Node.js patterns |
| Go | ✅ tree-sitter | ✅ package imports | — |

Config files (Dockerfile, GitHub Actions, Makefile, requirements.txt) are indexed as nodes in the dependency graph even without a full parser.

---

## Architecture

```
repobrain index /repo
      │
      ▼
┌─────────────────────────────────────────────────────┐
│            AsyncIndexingPipeline  (7 stages)         │
│                                                      │
│  1. Discovery    ──▶ file manifest to SQL            │
│  2. Parse        ──▶ ProcessPoolExecutor (CPU-bound) │
│  3. Graph Build  ─┐  concurrent                      │
│  4. Git Analysis ─┘  (asyncio.gather)                │
│  5. Embedding    ──▶ ThreadPoolExecutor + semaphore  │
│  6. RAG Doc Gen  ──▶ LanceDB deps fetched FIRST      │
│  7. Atomic Commit──▶ AtomicStorageCoordinator.txn()  │
└─────────────────────────────────────────────────────┘
      │
      ▼
┌──────────┐   ┌──────────────┐   ┌────────────────┐
│  SQLite  │   │   LanceDB    │   │ NetworkX Graph │
│ (files,  │   │ (embeddings, │   │ (dependency    │
│  metrics)│   │  docs)       │   │  graph)        │
└──────────┘   └──────────────┘   └────────────────┘
```

**Atomic transactions across all three stores:**
```python
async with coordinator.transaction() as txn:
    txn.pending_sql.append(...)
    txn.pending_vectors.append(...)
    txn.pending_edges.append(...)
# On exception: SQL rollback + vector delete + graph node removal — guaranteed.
```

---

## Privacy & Security

- **Self-hosted** — your code never leaves your machine
- **BYOK** — bring your own Anthropic API key
- **No telemetry** — zero usage data collected or transmitted
- **HMAC-SHA256** webhook validation for GitHub integrations
- **MIT license** — no AGPL restrictions, use commercially without a commercial license

---

## Screenshots

| `repobrain index` | `repobrain review` |
|---|---|
| ![index](docs/assets/screenshots/screenshot-index.svg) | ![review](docs/assets/screenshots/screenshot-review.svg) |

| `repobrain status` | `repobrain costs` |
|---|---|
| ![status](docs/assets/screenshots/screenshot-status.svg) | ![costs](docs/assets/screenshots/screenshot-costs.svg) |

**[Full interactive demo at pinexai.github.io/repobrain →](https://pinexai.github.io/repobrain)**

---

## Configuration

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...

REPOMIND_DATA_DIR=~/.repobrain          # index storage location
REPOMIND_MAX_COMMITS=10000              # git history depth (repowise hardcodes 500)
REPOMIND_DECAY_HALFLIFE_DAYS=180        # temporal scoring half-life
REPOMIND_GENERATION_CONCURRENCY=5       # parallel doc generation workers
REPOMIND_MCP_PORT=8766                  # MCP server port
REPOMIND_WEBHOOK_PORT=8765              # GitHub webhook port
REPOMIND_WEBHOOK_SECRET=your-secret    # HMAC-SHA256 webhook validation
```

---

## Documentation

Full docs at **[pinexai.github.io/repobrain](https://pinexai.github.io/repobrain)**

| Section | Link |
|---|---|
| Installation & Quick Start | [Getting Started](https://pinexai.github.io/repobrain/getting-started/quickstart/) |
| CLI Reference | [CLI Docs](https://pinexai.github.io/repobrain/cli/) |
| MCP Tools Reference | [MCP Docs](https://pinexai.github.io/repobrain/mcp/overview/) |
| Architecture Deep Dive | [Architecture](https://pinexai.github.io/repobrain/architecture/pipeline/) |
| Migrate from repowise | [Migration Guide](https://pinexai.github.io/repobrain/reference/migration/) |
| repobrain vs repowise | [Comparison](https://pinexai.github.io/repobrain/comparison/) |
| Python API Reference | [API Docs](https://pinexai.github.io/repobrain/reference/api/) |

---

## License

MIT — see [LICENSE](LICENSE).

Built by [pinexai](https://github.com/pinexai). Not affiliated with repowise.
