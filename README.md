# repobrain — Codebase Intelligence That Thinks Ahead

[![PyPI version](https://img.shields.io/pypi/v/repobrain.svg)](https://pypi.org/project/repobrain/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/pinexai/repobrain/actions/workflows/ci.yml/badge.svg)](https://github.com/pinexai/repobrain/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-pinexai.github.io%2Frepobrain-blue)](https://pinexai.github.io/repobrain)

> **10× faster indexing. RAG-aware documentation. PR blast radius. Temporal hotspots.**
>
> repobrain is a codebase intelligence MCP server for Claude that fixes every critical flaw in repowise — then goes further.

---

## What's Wrong With Repowise (and How We Fix It)

| # | Repowise Flaw | repobrain Fix |
|---|---------------|--------------|
| 1 | **RAG context never used during generation** — vector store populated but never queried | `RAGAwareDocGenerator` fetches dependency docs from LanceDB *before* every LLM call |
| 2 | **25+ min initial indexing** — no parallelism | 7-stage async pipeline; parse runs in `ProcessPoolExecutor`, git + parse run concurrently |
| 3 | **3 stores with no atomic transactions** — 5–15% silent consistency failures | `AtomicStorageCoordinator.transaction()` buffers + rolls back SQL, LanceDB, and NetworkX |
| 4 | **Hardcoded 500-commit limit** | `GitConfig.max_commits = 10_000` — fully configurable |
| 5 | **Dynamic imports invisible** (Django, pytest, importlib) — 20–40% missing graph edges | `DjangoDynamicHints`, `PytestDynamicHints`, `NodeDynamicHints` in `HintRegistry` |
| 6 | **Incremental updates miss global percentile recalculation** | `upsert()` always triggers `PERCENT_RANK()` window function refresh |
| 7 | **No PR blast radius analysis** | `PRBlastRadiusAnalyzer` + `repobrain review <PR>` + `get_pr_impact` MCP tool |
| 8 | **Temporal blindness** — 3-year-old commits weighted same as yesterday's | Exponential decay: `score += exp(-ln(2) * age_days / halflife) * complexity` |
| 9 | **Zero cost visibility** | `TokenspyCostAdapter` wraps every Anthropic call; `repobrain costs` CLI |
| 10 | **Conservative dead code** misses real candidates | Dynamic hint edges recovered; configurable sensitivity threshold |

---

## Installation

```bash
pip install repobrain
```

**Requirements:** Python 3.12+, an Anthropic API key.

---

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY

# 2. Index your repo
repobrain index /path/to/your/repo

# 3. Analyze a PR
repobrain review 42

# 4. Start MCP server for Claude Code
repobrain serve
```

Then add to your Claude Code MCP config:

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
|---------|-------------|
| `repobrain index [PATH]` | Index a repository (full or incremental) |
| `repobrain review <PR>` | Analyze PR blast radius and risk score |
| `repobrain serve` | Start MCP server (+ optional webhook) |
| `repobrain status` | Show hotspot rankings and index health |
| `repobrain query "<NL>"` | Natural language codebase search |
| `repobrain costs [--since DATE]` | Show per-operation LLM spend |

**Rich progress during indexing:**
```
[=====>     ] 47% | Stage: Generating Docs | Files: 234/500 | Cost: $0.23 | ETA: 4m12s
```

---

## MCP Tools (12 total)

| Tool | New? | Description |
|------|------|-------------|
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

## Architecture

```
repobrain index /repo
      |
      v
+-----------------------------------------------------+
|              AsyncIndexingPipeline (7 stages)        |
|                                                      |
|  1. Discovery    -> file manifest to SQL             |
|  2. Parse        -> ProcessPoolExecutor (CPU-bound)  |
|  3. Graph Build  -+  concurrent                      |
|  4. Git Analysis -+  (asyncio.gather)                |
|  5. Embedding    -> ThreadPoolExecutor + semaphore   |
|  6. RAG Doc Gen  -> LanceDB deps fetched FIRST       |
|  7. Atomic Commit-> AtomicStorageCoordinator.txn()   |
+-----------------------------------------------------+
      |
      v
+----------+   +--------------+   +----------------+
| SQLite   |   | LanceDB      |   | NetworkX Graph |
| (files,  |   | (embeddings, |   | (dependency    |
|  metrics)|   |  docs)       |   |  graph)        |
+----------+   +--------------+   +----------------+
```

**Atomic transactions across all three stores:**
```python
async with coordinator.transaction() as txn:
    txn.pending_sql.append(...)
    txn.pending_vectors.append(...)
    txn.pending_edges.append(...)
# On exception: SQL rollback + vector delete + graph node removal
```

---

## Configuration

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
REPOMIND_DATA_DIR=~/.repobrain
REPOMIND_MAX_COMMITS=10000
REPOMIND_DECAY_HALFLIFE_DAYS=180
REPOMIND_GENERATION_CONCURRENCY=5
REPOMIND_MCP_PORT=8766
REPOMIND_WEBHOOK_PORT=8765
REPOMIND_WEBHOOK_SECRET=your-github-webhook-secret
```

---

## Documentation

Full docs at **[pinexai.github.io/repobrain](https://pinexai.github.io/repobrain)**

- [Installation & Quick Start](https://pinexai.github.io/repobrain/getting-started/quickstart/)
- [CLI Reference](https://pinexai.github.io/repobrain/cli/)
- [MCP Tools Reference](https://pinexai.github.io/repobrain/mcp/overview/)
- [Architecture Deep Dive](https://pinexai.github.io/repobrain/architecture/pipeline/)
- [repobrain vs repowise](https://pinexai.github.io/repobrain/comparison/)

---

## License

MIT — see [LICENSE](LICENSE).

Built by [pinexai](https://github.com/pinexai).
