# Contributing

## Development Setup

```bash
git clone https://github.com/pinexai/repobrain.git
cd repobrain
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v --cov=repomind --cov-report=term-missing
```

Target: **80%+ coverage** on all PRs.

## Code Style

```bash
ruff check repomind/          # lint
ruff format repomind/         # format
mypy repomind/ --strict       # type check
```

All three must pass before opening a PR.

## Project Structure

```
repomind/           # Python package (internal name)
├── cli/            # Click CLI commands
├── config/         # pydantic-settings configuration
├── core/           # Coordinator + indexing pipeline
├── generation/     # RAGAwareDocGenerator + cost tracking
├── git/            # History, metrics, ownership, PR analysis
├── graph/          # CodeGraphBuilder + GraphAnalyzer
├── mcp/            # FastMCP server + 12 tools
├── parsing/        # Tree-sitter parsers + dynamic hints
├── storage/        # SQL, LanceDB, NetworkX adapters
├── utils/          # Hashing, file utilities, logging
└── webhook/        # FastAPI webhook server
```

## Adding a New Language Parser

1. Create `repomind/parsing/languages/yourlang.py` extending `BaseLanguageHandler`
2. Implement `parse(content: str) -> ParseResult`
3. Register in `repomind/parsing/languages/__init__.py`
4. Add tests in `tests/unit/test_parsing.py`

## Adding a New MCP Tool

1. Create `repomind/mcp/tools/your_tool.py`
2. Register with `@mcp.tool()` in `repomind/mcp/server.py`
3. Document in `docs/mcp/your-tool.md`
4. Add to the nav in `mkdocs.yml`

## Submitting a PR

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Write tests first (TDD)
4. Ensure all checks pass: `ruff check && mypy && pytest`
5. Open a PR with a clear description of the change and why
6. Link any related issues

## Reporting Bugs

Open an issue at [github.com/pinexai/repobrain/issues](https://github.com/pinexai/repobrain/issues) with:
- repobrain version (`repobrain --version`)
- OS and Python version
- Full error traceback
- Debug logs: `REPOMIND_LOG_LEVEL=DEBUG repobrain <command> 2>&1`
