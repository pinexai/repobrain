from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DepContext:
    file_path: str
    summary: str
    key_exports: str


class PromptTemplates:
    @staticmethod
    def doc_generation(
        file_path: str,
        file_content: str,
        language: str,
        symbols: list[str],
        dependency_contexts: list[DepContext],
        centrality: float = 0.0,
        hotspot_score: float = 0.0,
    ) -> str:
        dep_section = ""
        if dependency_contexts:
            dep_lines = "\n".join(
                f"### {dc.file_path}\n{dc.summary}\nKey exports: {dc.key_exports}"
                for dc in dependency_contexts[:10]  # cap at 10 deps to stay within token budget
            )
            dep_section = f"""
## Dependencies (what this file imports)

These are the actual docs for files this module imports.
Use them to write accurate descriptions of how this file uses its dependencies.

{dep_lines}
"""

        symbols_section = ""
        if symbols:
            symbols_section = f"\n## Key Symbols\n{chr(10).join(f'- {s}' for s in symbols[:30])}"

        metrics_section = ""
        if centrality > 0 or hotspot_score > 0:
            metrics_section = f"""
## Code Metrics
- Centrality (architectural importance): {centrality:.3f}
- Hotspot score (churn × complexity): {hotspot_score:.3f}
"""

        return f"""You are a senior software engineer documenting a codebase.
Write a concise technical documentation page for the following {language} file.

## File: {file_path}
{metrics_section}
{dep_section}
{symbols_section}

## Source Code
```{language}
{file_content[:6000]}
```

Write documentation that covers:
1. **Purpose**: What this module does and why it exists (1-2 sentences)
2. **Key responsibilities**: Bullet list of what it does
3. **Public API**: Most important functions/classes/exports with brief descriptions
4. **Dependencies**: How it uses its imported modules (reference the dependency docs above)
5. **Usage notes**: Any gotchas, important patterns, or architectural decisions

Be concise and precise. Avoid generic filler text. Use the dependency docs to write accurate descriptions."""

    @staticmethod
    def architectural_decision(
        file_path: str,
        commit_messages: list[str],
        file_summary: str,
    ) -> str:
        messages = "\n".join(f"- {m}" for m in commit_messages[:20])
        return f"""You are analyzing git history to extract architectural decisions.

File: {file_path}
File summary: {file_summary}

Recent significant commit messages:
{messages}

Identify architectural decisions embedded in this history.
For each decision found, output:

DECISION: <title>
CONTEXT: <why this decision was made>
DECISION_TEXT: <what was decided>
CONSEQUENCES: <trade-offs and implications>

Only extract meaningful architectural decisions (not bug fixes or minor changes).
Return NONE if no significant architectural decisions are found."""

    @staticmethod
    def security_analysis(
        file_path: str,
        file_content: str,
        symbols: list[str],
    ) -> str:
        return f"""Analyze this {file_path} for security-sensitive patterns.

```
{file_content[:4000]}
```

Symbols: {', '.join(symbols[:20])}

Identify security hotspots:
- Authentication/authorization logic
- Input deserialization or validation
- SQL construction (potential injection)
- Credential or secret handling
- External API calls with user-controlled data
- Rate limiting absence

For each issue found:
SEVERITY: critical|high|medium
PATTERN: <pattern type>
LINE: <approximate line number>
EVIDENCE: <what you found>
RECOMMENDATION: <what to do>

Return NONE if no significant security concerns found."""
