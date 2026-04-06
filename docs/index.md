# repobrain

**Codebase intelligence that thinks ahead.**

[![PyPI version](https://img.shields.io/pypi/v/repobrain.svg)](https://pypi.org/project/repobrain/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/pinexai/repobrain/blob/main/LICENSE)
[![CI](https://github.com/pinexai/repobrain/actions/workflows/ci.yml/badge.svg)](https://github.com/pinexai/repobrain/actions/workflows/ci.yml)

repobrain is an MCP server for Claude that gives it deep, always-fresh understanding of your codebase — 10× faster indexing, RAG-aware documentation, PR blast radius, and temporal hotspot scoring.

---

## Live Demo

<div id="demo-player" class="ap-wrapper"></div>

<link rel="stylesheet" type="text/css" href="assets/asciinema-player.css" />
<script>
  document.addEventListener("DOMContentLoaded", function(){
    AsciinemaPlayer.create("assets/demo.cast", document.getElementById("demo-player"), {
      cols: 120, rows: 35, autoPlay: true, loop: true, speed: 1.5,
      theme: "monokai", fit: "width",
      terminalFontFamily: "'JetBrains Mono', 'Fira Code', monospace"
    });
  });
</script>

---

## Screenshots

### `repobrain index` — 7-stage async pipeline

<img class="screenshot" src="assets/screenshots/screenshot-index.svg" alt="repobrain index" />

### `repobrain status` — Temporal hotspot rankings

<img class="screenshot" src="assets/screenshots/screenshot-status.svg" alt="repobrain status" />

### `repobrain review 42` — PR blast radius analysis

<img class="screenshot" src="assets/screenshots/screenshot-review.svg" alt="repobrain review 42" />

### `repobrain costs` — LLM spend by operation

<img class="screenshot" src="assets/screenshots/screenshot-costs.svg" alt="repobrain costs" />

### MCP Tools — 12 tools available in Claude Code

<img class="screenshot" src="assets/screenshots/screenshot-mcp-tools.svg" alt="repobrain MCP Tools" />

---

## Why repobrain?

After analyzing repowise in depth, we found **10 critical architectural flaws**. repobrain fixes every one:

| # | Repowise Flaw | repobrain Fix |
|---|---------------|--------------|
| 1 | RAG context never used during generation | Dependency docs fetched from LanceDB *before* every LLM call |
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

See the [Quick Start guide](getting-started/quickstart.md) for full setup, or [migrate from repowise](reference/migration.md) in 5 minutes.
