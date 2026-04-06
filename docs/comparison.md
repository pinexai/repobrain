# repobrain vs. repowise

## Feature Comparison

| Feature | repowise | repobrain |
|---------|----------|----------|
| Initial indexing time | 25+ min | ~3–5 min |
| RAG docs use dependency context | No | Yes |
| Atomic transactions (3 stores) | No | Yes |
| Git commit limit | 500 (hardcoded) | 10,000 (configurable) |
| Dynamic import edges (Django/pytest/Node) | No | Yes |
| Global percentile rank refresh on incremental | No | Yes |
| PR blast radius analysis | No | Yes |
| Temporal decay scoring | No | Yes |
| LLM cost visibility | No | Yes |
| Dead code sensitivity (configurable) | No | Yes |
| MCP tools | 8 | 12 |
| CLI commands | 4 | 6 |
| GitHub webhook auto-index | Partial | Full (HMAC-SHA256) |

## Architectural Comparison

### Documentation Generation

**repowise:**
```python
# Vector store populated but never queried during generation
async def generate_docs(file):
    prompt = f"Document this file:\n{file.content}"
    return await llm.complete(prompt)
```

**repobrain:**
```python
# Dependency docs fetched BEFORE LLM call
async def generate(file_path, parse_result, graph):
    dep_paths = graph.get_direct_dependencies(file_path)
    dep_contexts = await retriever.get_docs(dep_paths)  # <- THE FIX
    prompt = build_prompt(
        file_content=...,
        dependency_contexts=dep_contexts,  # actual dep docs included
        centrality=...,
        hotspot_score=...,
    )
    return await llm.complete(prompt)
```

### Storage Consistency

**repowise:**
```python
# Three independent writes — any can fail silently
await sql_store.save(file)
await vector_store.save(file)
graph_store.add_node(file)
```

**repobrain:**
```python
# Atomic — all succeed or all roll back
async with coordinator.transaction() as txn:
    txn.pending_sql_calls.append(...)
    txn.pending_vector_records.append(...)
    txn.pending_nodes.append(...)
```

### Hotspot Scoring

**repowise:**
```python
# All commits equally weighted — 3-year-old commits same as yesterday's
score = sum(commit.lines_changed for commit in commits)
```

**repobrain:**
```python
# Exponential decay — recent activity matters more
for commit in commits:
    age_days = (now - commit.authored_date).days
    decay = exp(-ln(2) * age_days / 180)
    score += decay * min(commit.lines_changed / 100, 3.0)
```

## Migration from repowise

repobrain is a drop-in replacement. The MCP tool names are compatible. Simply:

1. `pip install repobrain`
2. `repobrain index /your/repo`
3. Update your MCP server config from repowise to repobrain
4. Access all 12 tools (8 familiar + 4 new)
