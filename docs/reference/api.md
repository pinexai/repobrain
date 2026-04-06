# API Reference

## Python API

repobrain can be used as a library — not just a CLI.

### AsyncIndexingPipeline

```python
from repomind.core.indexer import AsyncIndexingPipeline
from repomind.config.schema import RepomindConfig

config = RepomindConfig()
pipeline = AsyncIndexingPipeline(config)

async def main():
    await pipeline.run(
        repo_path="/path/to/repo",
        incremental=True,
        generate_docs=True,
    )
```

### AtomicStorageCoordinator

```python
from repomind.core.coordinator import AtomicStorageCoordinator
from repomind.storage.sql import AsyncSQLiteDB
from repomind.storage.vector import LanceDBStore
from repomind.storage.graph import GraphStore

db = AsyncSQLiteDB("~/.repomind/repo.db")
vector = LanceDBStore("~/.repomind/vectors")
graph = GraphStore("~/.repomind/graph.graphml")

await db.connect()
await vector.connect()

coord = AtomicStorageCoordinator(db, vector, graph)

async with coord.transaction() as txn:
    txn.pending_nodes.append(("src/main.py", {"type": "file", "language": "python"}))
    txn.pending_edges.append(("src/main.py", "src/utils.py", {"type": "imports"}))
```

### PRBlastRadiusAnalyzer

```python
from repomind.git.pr_analyzer import PRBlastRadiusAnalyzer

analyzer = PRBlastRadiusAnalyzer(
    graph_store=graph,
    db=db,
    repo_id="abc123",
)

report = await analyzer.analyze_files(
    changed_files=["src/auth/login.py", "src/auth/tokens.py"],
    pr_title="Add OAuth2 login",
)

print(f"Risk score: {report.overall_risk_score}/10")
for f in report.transitive_files:
    print(f"  {f.file_path}  risk={f.risk_score:.1f}")
```

### GraphStore

```python
from repomind.storage.graph import GraphStore

g = GraphStore("graph.graphml")

g.add_node("src/main.py", type="file", language="python", centrality=0.8)
g.add_edge("src/main.py", "src/utils.py", type="imports")

# Queries
ancestors = g.ancestors("src/utils.py")   # all files that depend on utils.py
pr = g.pagerank()                          # centrality scores
dead = g.find_dead_code(["src/main.py"])  # unreachable from entry points
```

### TemporalMetricsCalculator

```python
from repomind.git.metrics import TemporalMetricsCalculator

calc = TemporalMetricsCalculator(halflife_days=180)
score = calc.compute(commits)  # list of GitCommit objects
```

---

## Configuration Reference

All settings via `pydantic-settings` — set as env vars or in `.env`.

### RepomindConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data_dir` | Path | `~/.repomind` | Index storage root |
| `log_level` | str | `INFO` | Logging level |

### GitConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_commits` | int | `10000` | Max commits to analyze |
| `decay_halflife_days` | float | `180.0` | Temporal decay halflife |
| `branch` | str | `None` | Git branch (default: current) |

### LLMConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model` | str | `claude-sonnet-4-6` | Anthropic model ID |
| `max_tokens` | int | `2048` | Max tokens per doc generation |

### IndexingConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `generation_concurrency` | int | `5` | Max concurrent LLM calls |
| `embedding_concurrency` | int | `10` | Max concurrent embedding calls |
| `max_file_size_kb` | int | `500` | Skip files larger than this |

### MCPConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `port` | int | `8766` | MCP server port |
| `host` | str | `127.0.0.1` | Bind address |

### WebhookConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `port` | int | `8765` | Webhook server port |
| `secret` | str | `None` | HMAC-SHA256 secret |
| `github_token` | str | `None` | Token for posting PR comments |
