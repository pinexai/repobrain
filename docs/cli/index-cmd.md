# repomind index

Index a repository for codebase intelligence.

## Usage

```bash
repomind index [PATH] [OPTIONS]
```

`PATH` defaults to the current directory.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--full` | — | Force full re-index (default on first run) |
| `--incremental` | — | Only process changed files since last index |
| `--max-commits N` | 10000 | Override commit history depth |
| `--concurrency N` | 5 | Override generation concurrency |
| `--no-docs` | — | Skip doc generation (faster, no LLM calls) |
| `--language LANG` | all | Restrict to a specific language |

## Pipeline Stages

1. **Discovery** — walk repo, detect languages, write file manifest to SQL
2. **Parse** — tree-sitter parsing in `ProcessPoolExecutor` (CPU-bound)
3. **Graph Build** — async as ParseResults stream in (concurrent with Stage 4)
4. **Git Analysis** — commit history, ownership, co-change patterns
5. **Embedding** — `ThreadPoolExecutor` + semaphore-limited batch embedding
6. **RAG Doc Generation** — dependency docs fetched from LanceDB FIRST, then LLM called
7. **Atomic Commit** — per-file `coordinator.transaction()` — rolls back all 3 stores on failure

## Examples

```bash
# Index current directory
repomind index

# Full re-index of a specific repo
repomind index /path/to/repo --full

# Incremental update (changed files only)
repomind index --incremental

# Skip docs, just rebuild graph and metrics
repomind index --no-docs --incremental
```
