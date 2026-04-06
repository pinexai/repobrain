# Atomic Transactions

repobrain maintains three stores: SQLite (metadata + metrics), LanceDB (embeddings + docs), and NetworkX (dependency graph). Writing to all three atomically is the key innovation that prevents the 5–15% silent consistency failures in repowise.

## The Problem (repowise)

repowise writes to each store independently. If the process crashes between writes:
- SQL has the file record, LanceDB doesn't
- The graph has an edge to a file that has no embedding
- Incremental updates skip files that are "already indexed" in SQL but missing from LanceDB

These inconsistencies are silent — no error is raised.

## The Solution (AtomicStorageCoordinator)

```python
async with coordinator.transaction() as txn:
    txn.pending_sql_calls.append(lambda: repo.upsert(...))
    txn.pending_vector_records.append({"id": file_id, ...})
    txn.pending_nodes.append(("src/main.py", {"type": "file", ...}))
    txn.pending_edges.append(("src/main.py", "src/utils.py", {}))

# On success: flush SQL → graph → vector (in order)
# On exception: SQL rollback + delete buffered vector IDs + remove buffered graph nodes
```

## Rollback Behavior

| Store | On Success | On Exception |
|-------|------------|--------------|
| SQLite | `COMMIT` | `ROLLBACK` |
| LanceDB | Insert records | Delete by buffered IDs |
| NetworkX | Add nodes + edges | Remove buffered nodes + edges |

## Health Check

```python
health = await coordinator.health_check(repo_id)
# {
#   "sql_files": 500,
#   "graph_nodes": 500,
#   "vector_records": 500,
#   "consistent": true
# }
```

Use `repobrain status` to run a health check interactively.
