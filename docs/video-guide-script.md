# repobrain Video Guide Script

**Duration:** ~5 minutes
**Format:** Screen recording with narration
**Tool:** asciinema or QuickTime

---

## 0:00 — Hook (30s)

**[Show split screen: repowise indexing slowly vs repobrain progress bar]**

> "If you've used repowise, you know the pain — 25 minutes to index a medium-sized repo, documentation that ignores what your files actually import, and no way to know which files a PR will actually break. repobrain fixes all of that."

---

## 0:30 — Install (30s)

**[Terminal — clean shell]**

```bash
pip install repobrain
repobrain --version
```

> "One pip install. No Docker, no separate database server — everything runs locally."

---

## 1:00 — Configure (30s)

**[Show .env.example, then editing .env]**

```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY
```

> "Just set your Anthropic API key. Everything else has sensible defaults."

---

## 1:30 — Index (60s)

**[Show Rich progress bar with all 7 stages]**

```bash
repobrain index /path/to/repo
```

> "Watch the 7-stage pipeline. Parsing runs in parallel processes, git analysis runs concurrently with graph building, and every write is atomic across all three stores — SQLite, LanceDB, and the NetworkX graph."

**[Point out the stage indicator and cost tracker]**

> "Notice the real-time cost counter. Unlike repowise, every LLM call is tracked."

---

## 2:30 — Status (30s)

**[Show hotspot table]**

```bash
repobrain status
```

> "Hotspots are ranked by temporal decay scoring — files changed frequently *recently* rank higher than files with high historical churn but no recent activity."

---

## 3:00 — PR Blast Radius (60s)

**[Show repobrain review output with direct + transitive files]**

```bash
repobrain review 42
```

> "This is the feature repowise doesn't have at all. repobrain traverses the dependency graph to find every file that imports your changed files — not just the direct changes. And it warns you when a file that's historically changed together with your PR files is missing."

**[Point at co-change warning and recommended reviewers]**

> "It even recommends reviewers based on who owns the affected files."

---

## 3:45 — MCP Tools in Claude Code (45s)

**[Show Claude Code with repobrain MCP server connected]**

```bash
repobrain serve --mcp-only
```

> "Start the MCP server and add it to Claude Code. Now Claude has 12 tools to understand your codebase — including the 4 new tools repowise doesn't have."

**[Show Claude using get_pr_impact and get_knowledge_map]**

> "Ask Claude to analyze a PR's impact, or find knowledge silos before someone leaves your team."

---

## 4:30 — Costs (30s)

**[Show repobrain costs table]**

```bash
repobrain costs --by operation
```

> "See exactly what you're spending — broken down by operation, file, model, or day. Powered by tokenspy."

---

## 5:00 — Outro

**[Show GitHub repo and PyPI badge]**

> "repobrain is open source under MIT. Install it with pip install repobrain, star the repo, and file issues on GitHub. Links below."

---

## Recording Notes

- Use `asciinema rec` for terminal recording
- Convert to GIF: `agg demo.cast demo.gif` (requires [agg](https://github.com/asciinema/agg))
- Embed in README: `![repobrain demo](docs/assets/demo.gif)`
- Recommended terminal: iTerm2, 180×40 cols, JetBrains Mono 14pt
