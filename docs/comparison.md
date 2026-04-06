# repobrain vs. repowise

A head-to-head comparison of every capability, architecture decision, and tradeoff.

---

## At a Glance

| Metric | repowise | repobrain |
|---|---|---|
| Initial indexing (1,000 files) | ~25 min | ~3–5 min |
| Git history depth | 500 commits (hardcoded) | 10,000 (configurable) |
| Missing import edges | 20–40% | ~0% (dynamic hints) |
| Silent consistency failures | 5–15% | 0% (atomic transactions) |
| MCP tools | 8 | **12** |
| CLI commands | 4 | **6** |
| Temporal scoring | ❌ | ✅ exponential decay |
| PR blast radius | ❌ | ✅ |
| LLM cost tracking | ❌ | ✅ |
| License | AGPL-3.0 | **MIT** |
| Self-hosted | ✅ | ✅ |
| RAG used during generation | ❌ | **✅** |

---

## Full Feature Matrix

### Documentation Generation

| Feature | repowise | repobrain |
|---|---|---|
| Generates file-level docs | ✅ | ✅ |
| Generates symbol-level docs | ✅ | ✅ |
| Fetches dependency context before generation | ❌ | ✅ |
| Includes centrality score in prompt | ❌ | ✅ |
| Includes hotspot score in prompt | ❌ | ✅ |
| Freshness / staleness tracking | Basic | Advanced |
| Semantic search over generated docs | ✅ | ✅ |

### Git Analysis

| Feature | repowise | repobrain |
|---|---|---|
| Commit history depth | 500 (hardcoded) | 10,000 (configurable) |
| Hotspot scoring | Linear count | **Exponential decay** |
| Co-change analysis | ✅ | ✅ temporal-weighted |
| Ownership calculation | ✅ | ✅ temporal-weighted |
| Architectural decision capture | ✅ | ✅ |
| Percentile rank refresh on incremental update | ❌ | ✅ |

### Graph Construction

| Feature | repowise | repobrain |
|---|---|---|
| Python parsing | ✅ tree-sitter | ✅ tree-sitter |
| TypeScript parsing | ✅ | ✅ |
| Go parsing | ✅ | ✅ |
| JavaScript parsing | ✅ | ✅ |
| Django dynamic imports | ❌ | ✅ |
| pytest fixture imports | ❌ | ✅ |
| Node.js require() patterns | ❌ | ✅ |
| PageRank centrality | ✅ | ✅ |
| Transitive dependency traversal | ✅ | ✅ |

### Storage & Reliability

| Feature | repowise | repobrain |
|---|---|---|
| SQL store (SQLite) | ✅ | ✅ |
| Vector store (LanceDB) | ✅ | ✅ |
| Graph store (NetworkX) | ✅ | ✅ |
| Atomic transactions across all 3 | ❌ | ✅ |
| Rollback on partial failure | ❌ | ✅ |
| Consistency failure rate | 5–15% | ~0% |

### MCP Tools

| Tool | repowise | repobrain | Improvements |
|---|---|---|---|
| `explain_file` | ✅ | ✅ | RAG-injected dependency context |
| `explain_symbol` | ✅ | ✅ | Same |
| `get_hotspots` | ✅ | ✅ | Temporal decay scoring |
| `get_ownership` | ✅ | ✅ | Temporal-weighted |
| `get_dependencies` | ✅ | ✅ | Dynamic hint edges included |
| `get_architectural_decisions` | ✅ | ✅ | Same |
| `search_codebase` | ✅ | ✅ | Same |
| `get_cochange_patterns` | ✅ | ✅ | Temporal-weighted |
| `get_pr_impact` | ❌ | **✅ NEW** | — |
| `get_knowledge_map` | ❌ | **✅ NEW** | — |
| `get_test_gaps` | ❌ | **✅ NEW** | — |
| `get_security_hotspots` | ❌ | **✅ NEW** | — |

### CLI

| Command | repowise | repobrain |
|---|---|---|
| `index` / `init` | ✅ | ✅ faster |
| `serve` | ✅ | ✅ |
| `query` | ✅ | ✅ |
| `status` | ✅ | ✅ |
| `review <PR>` | ❌ | **✅ NEW** |
| `costs` | ❌ | **✅ NEW** |

### Security & Privacy

| Feature | repowise | repobrain |
|---|---|---|
| Self-hosted | ✅ | ✅ |
| Code stays local | ✅ | ✅ |
| BYOK (bring your own API key) | ✅ | ✅ |
| No telemetry | ✅ | ✅ |
| GitHub webhook HMAC-SHA256 validation | Partial | **Full** |
| License | AGPL-3.0 | **MIT** |
| Commercial use without license fee | ❌ (AGPL) | **✅ (MIT)** |

---

## Architecture Comparison

### Documentation Generation — The #1 Flaw

**repowise** populates a vector store during indexing but **never queries it** when generating documentation. Each file's docs are generated with no knowledge of its dependencies.

```python
# repowise (simplified)
async def generate_docs(file):
    prompt = f"Document this file:\n{file.content}"
    return await llm.complete(prompt)  # no dependency context
```

**repobrain** fetches dependency documentation from LanceDB *before* every LLM call:

```python
# repobrain
async def generate(file_path, parse_result, graph):
    dep_paths = graph.get_direct_dependencies(file_path)
    dep_contexts = await retriever.get_docs(dep_paths)  # ← the fix
    prompt = build_prompt(
        file_content=parse_result.content,
        dependency_contexts=dep_contexts,   # actual dep docs included
        centrality=graph.get_centrality(file_path),
        hotspot_score=metrics.get_score(file_path),
    )
    return await llm.complete(prompt)
```

### Storage Consistency — Silent Failures

**repowise** writes to three independent stores with no coordination. Any write can fail silently, leaving indexes in an inconsistent state (5–15% failure rate under load).

```python
# repowise — three independent writes
await sql_store.save(file_record)
await vector_store.upsert(embedding)
graph_store.add_node(file_path)   # if this crashes, SQL and vector are already written
```

**repobrain** wraps all three in an atomic transaction — all succeed or all roll back:

```python
# repobrain — atomic across all 3 stores
async with coordinator.transaction() as txn:
    txn.pending_sql_calls.append(lambda: sql.save(file_record))
    txn.pending_vector_records.append(embedding)
    txn.pending_nodes.append(file_path)
# On any exception: SQL rollback + vector delete + graph node removal
```

### Hotspot Scoring — Temporal Blindness

**repowise** treats a commit from 3 years ago the same as a commit from yesterday:

```python
# repowise — linear accumulation
score = sum(commit.lines_changed for commit in commits[-500:])
```

**repobrain** applies exponential decay so recent activity dominates:

```python
# repobrain — temporal decay
from math import exp, log

for commit in commits:
    age_days = (now - commit.authored_date).days
    decay = exp(-log(2) * age_days / halflife_days)   # halflife default: 180 days
    normalized = min(commit.lines_changed / 100, 3.0)  # cap outliers
    score += decay * normalized
```

---

## Performance Comparison

| Benchmark | repowise | repobrain | Improvement |
|---|---|---|---|
| 1,000-file Python repo — first index | ~25 min | ~3–5 min | **5–8× faster** |
| 1,000-file repo — incremental update (50 files) | ~3 min | ~30 sec | **6× faster** |
| Embedding concurrency | Sequential | ThreadPoolExecutor + semaphore | parallel |
| Parse stage | Single process | ProcessPoolExecutor (multi-core) | CPU-bound speedup |
| Git + parse stages | Sequential | `asyncio.gather` (concurrent) | concurrent |

---

## Licensing

| Aspect | repowise | repobrain |
|---|---|---|
| License | AGPL-3.0 | **MIT** |
| Commercial use | Requires commercial license | Free — no restrictions |
| Modify and redistribute | Must open-source changes | No requirement |
| SaaS / hosted deployment | Requires commercial license | Free |
| Cost | Free (open-source) + paid plans | Free — MIT forever |

**repowise is AGPL-3.0** — if you deploy it in a commercial product or SaaS, the AGPL requires you to release your entire application under AGPL or purchase a commercial license from repowise-dev.

**repobrain is MIT** — use it commercially, integrate it into proprietary software, deploy it as a SaaS. No license fees, no restrictions.

---

## Migration from repowise

repobrain is API-compatible with repowise. All 8 repowise MCP tool names work unchanged. Migration takes under 5 minutes.

[See the Migration Guide →](reference/migration.md)
