# Changelog

All notable changes to repobrain are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

## [0.1.0] — 2026-04-06

### Added

- **AtomicStorageCoordinator** — context manager that buffers writes across SQL + LanceDB + NetworkX and rolls back all three on failure
- **AsyncIndexingPipeline** — 7-stage parallel pipeline; parse stage runs in `ProcessPoolExecutor`, git analysis runs concurrently with graph building
- **RAGAwareDocGenerator** — fetches dependency docs from LanceDB *before* every LLM call (fixes repowise's #1 flaw)
- **TemporalMetricsCalculator** — exponential decay scoring `exp(-ln(2) * age_days / halflife)` weights recent commits higher
- **PRBlastRadiusAnalyzer** — direct + transitive graph traversal, risk scoring 0–10, co-change warnings, reviewer recommendations
- **Dynamic import hints** — `DjangoDynamicHints`, `PytestDynamicHints`, `NodeDynamicHints` recover 20–40% missing graph edges
- **12 MCP tools** — 8 improved from repowise + 4 new: `get_pr_impact`, `get_knowledge_map`, `get_test_gaps`, `get_security_hotspots`
- **6 CLI commands** — `index`, `review`, `serve`, `status`, `query`, `costs`
- **GitHub webhook server** — HMAC-SHA256 validated, incremental re-index on push, blast radius on PR open/sync
- **TokenspyCostAdapter** — tracks per-operation LLM spend via tokenspy
- **Configurable git depth** — `GitConfig.max_commits = 10_000` (repowise hardcodes 500)
- **Percentile rank refresh** — `GitMetricsRepository.upsert()` always triggers `PERCENT_RANK()` window function refresh
