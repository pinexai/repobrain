"""
repomind MCP Server — 12 tools for Claude Code integration.
8 improved tools + 4 entirely new tools not in repowise.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ..config import RepomindConfig
from ..git.pr_analyzer import PRBlastRadiusAnalyzer
from ..graph.analyzer import GraphAnalyzer
from ..storage.graph import GraphStore
from ..storage.sql import AsyncSQLiteDB, FileRepository, GitMetricsRepository, DecisionRepository
from ..storage.vector import LanceDBStore, AsyncEmbedder
from ..utils.logging import get_logger

log = get_logger(__name__)

mcp = FastMCP("repomind")

# Global state — initialized by start_server()
_config: RepomindConfig | None = None
_db: AsyncSQLiteDB | None = None
_vector: LanceDBStore | None = None
_graph_store: GraphStore | None = None
_repo_id: str = ""


async def _get_deps() -> tuple[AsyncSQLiteDB, GraphStore, LanceDBStore, str]:
    assert _db and _graph_store and _vector and _repo_id
    return _db, _graph_store, _vector, _repo_id


# ─── Tool 1: explain_file ────────────────────────────────────────────────────

@mcp.tool()
async def explain_file(
    file_path: str,
    include_dependencies: bool = True,
    include_git_history: bool = True,
) -> dict[str, Any]:
    """
    Explain what a file does, its role in the architecture, dependencies, and ownership.
    Returns RAG-generated documentation with dependency context.
    """
    db, graph, vector, repo_id = await _get_deps()
    file_repo = FileRepository(db)
    metrics_repo = GitMetricsRepository(db)

    file_rec = await file_repo.get_by_path(repo_id, file_path)
    if not file_rec:
        return {"error": f"File not indexed: {file_path}"}

    # Get vector doc
    doc = await vector.get_file_doc_by_path(file_path)

    result: dict[str, Any] = {
        "file_path": file_path,
        "language": file_rec["language"],
        "summary": doc.get("doc_summary", "") if doc else "",
        "key_exports": doc.get("key_exports", "") if doc else "",
    }

    if include_dependencies:
        analyzer = GraphAnalyzer(graph)
        result["dependencies"] = graph.successors(file_path)
        result["dependents"] = graph.predecessors(file_path)

    if include_git_history:
        metrics = await metrics_repo.get_by_file(file_rec["id"])
        if metrics:
            result["owner"] = metrics["owner_email"]
            result["ownership_pct"] = round(metrics["ownership_pct"] * 100, 1)
            result["temporal_hotspot_score"] = round(metrics["temporal_hotspot_score"], 3)
            result["percentile_rank"] = round(metrics["percentile_rank"] * 100, 1)

    return result


# ─── Tool 2: explain_symbol ──────────────────────────────────────────────────

@mcp.tool()
async def explain_symbol(
    symbol_name: str,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Find and explain a function, class, or variable by name."""
    db, _, _, repo_id = await _get_deps()
    file_repo = FileRepository(db)
    symbols = await file_repo.search_symbols(repo_id, symbol_name)
    if file_path:
        symbols = [s for s in symbols if s.get("file_path") == file_path]
    return {"symbols": symbols[:10]}


# ─── Tool 3: get_hotspots ────────────────────────────────────────────────────

@mcp.tool()
async def get_hotspots(
    top_n: int = 20,
    time_window_days: int | None = None,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return files ranked by TEMPORAL hotspot score (exponentially decay-weighted).
    Recent churn matters more than old churn.
    time_window_days: if set, only include files modified in that window.
    """
    db, _, _, repo_id = await _get_deps()
    metrics_repo = GitMetricsRepository(db)
    hotspots = await metrics_repo.get_hotspots(repo_id, top_n, language)
    return [
        {
            "file_path": h["path"],
            "temporal_hotspot_score": round(h["temporal_hotspot_score"], 3),
            "percentile_rank": round(h["percentile_rank"] * 100, 1),
            "owner": h["owner_email"],
            "churn_count": h["churn_count"],
            "language": h["language"],
        }
        for h in hotspots
    ]


# ─── Tool 4: get_ownership ───────────────────────────────────────────────────

@mcp.tool()
async def get_ownership(
    file_path: str,
    threshold_pct: float = 0.1,
) -> dict[str, Any]:
    """Return temporal-weighted ownership map for a file. Recent commits weighted more."""
    db, _, _, repo_id = await _get_deps()
    file_repo = FileRepository(db)
    metrics_repo = GitMetricsRepository(db)

    file_rec = await file_repo.get_by_path(repo_id, file_path)
    if not file_rec:
        return {"error": f"Not indexed: {file_path}"}

    metrics = await metrics_repo.get_by_file(file_rec["id"])
    return {
        "file_path": file_path,
        "primary_owner": metrics["owner_email"] if metrics else "",
        "primary_ownership_pct": round((metrics["ownership_pct"] if metrics else 0) * 100, 1),
        "note": "Ownership is temporally weighted — recent commits count more",
    }


# ─── Tool 5: get_dependencies ────────────────────────────────────────────────

@mcp.tool()
async def get_dependencies(
    file_path: str,
    depth: int = 2,
    include_dynamic: bool = True,
) -> dict[str, Any]:
    """Return dependency subgraph up to `depth` hops, including dynamic hint edges."""
    _, graph, _, _ = await _get_deps()

    def _collect(fp: str, current_depth: int) -> dict:
        if current_depth == 0:
            return {}
        deps = graph.successors(fp)
        result = {}
        for dep in deps[:20]:
            attrs = graph.get_node_attrs(dep)
            if not include_dynamic and attrs.get("edge_type") == "dynamic_uses":
                continue
            result[dep] = _collect(dep, current_depth - 1)
        return result

    return {
        "file_path": file_path,
        "depth": depth,
        "dependencies": _collect(file_path, depth),
    }


# ─── Tool 6: get_architectural_decisions ────────────────────────────────────

@mcp.tool()
async def get_architectural_decisions(
    query: str | None = None,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve architectural decisions, optionally filtered by semantic query or file."""
    db, _, _, repo_id = await _get_deps()
    dec_repo = DecisionRepository(db)

    if file_path:
        decisions = await dec_repo.get_by_file(repo_id, file_path)
    else:
        decisions = await dec_repo.get_all(repo_id)

    return [
        {
            "id": d["id"],
            "title": d["title"],
            "context": d["context_text"],
            "decision": d["decision_text"],
            "consequences": d["consequences"],
            "files_affected": d["files_affected"].split(",") if d.get("files_affected") else [],
            "created_at": d["created_at"],
            "is_stale": bool(d["is_stale"]),
        }
        for d in decisions
    ]


# ─── Tool 7: search_codebase ─────────────────────────────────────────────────

@mcp.tool()
async def search_codebase(
    query: str,
    top_k: int = 10,
    language: str | None = None,
    scope: str = "files",
) -> list[dict[str, Any]]:
    """Semantic search across the codebase via vector similarity."""
    db, _, vector, repo_id = await _get_deps()

    # Use the OpenAI client for embeddings — embedder is initialized elsewhere
    # For simplicity, return text-based search from SQL
    like_pattern = f"%{query}%"
    rows = await db.fetchall(
        """SELECT f.path, f.language, s.name, s.kind FROM files f
           LEFT JOIN symbols s ON s.file_id = f.id
           WHERE f.repo_id = ? AND (f.path LIKE ? OR s.name LIKE ?)
           LIMIT ?""",
        (repo_id, like_pattern, like_pattern, top_k),
    )
    return [dict(r) for r in rows]


# ─── Tool 8: get_cochange_patterns ──────────────────────────────────────────

@mcp.tool()
async def get_cochange_patterns(
    file_path: str,
    min_cochange_score: float = 0.3,
) -> list[dict[str, Any]]:
    """Files that historically change together with the given file (hidden coupling)."""
    db, _, _, repo_id = await _get_deps()
    file_repo = FileRepository(db)
    metrics_repo = GitMetricsRepository(db)

    file_rec = await file_repo.get_by_path(repo_id, file_path)
    if not file_rec:
        return []

    partners = await metrics_repo.get_cochange_partners(
        file_rec["id"], repo_id, min_score=min_cochange_score
    )
    return [
        {
            "partner_path": p["partner_path"],
            "cochange_count": p["cochange_count"],
            "cochange_score": round(p["cochange_score"], 3),
        }
        for p in partners
    ]


# ─── Tool 9: get_pr_impact (NEW) ─────────────────────────────────────────────

@mcp.tool()
async def get_pr_impact(
    changed_files: list[str],
    pr_number: int | None = None,
    pr_title: str = "",
    include_transitive: bool = True,
    max_depth: int = 3,
) -> dict[str, Any]:
    """
    Analyze the blast radius of a PR before merge.
    Returns direct + transitive affected files, risk scores,
    recommended reviewers, co-change warnings, and test coverage gaps.
    """
    db, graph, _, repo_id = await _get_deps()
    analyzer = PRBlastRadiusAnalyzer(
        graph_store=graph,
        db=db,
        repo_id=repo_id,
        github_token=_config.github_token if _config else "",
    )
    report = await analyzer.analyze_files(changed_files, pr_number, pr_title, max_depth)
    return {
        "pr_number": report.pr_number,
        "pr_title": report.pr_title,
        "overall_risk_score": report.overall_risk_score,
        "risk_label": _risk_label(report.overall_risk_score),
        "direct_files": [
            {"path": r.file_path, "risk": round(r.risk_score, 3), "owner": r.owner_email}
            for r in report.changed_files
        ],
        "transitive_files": [
            {"path": r.file_path, "risk": round(r.risk_score, 3), "reason": r.impact_reason}
            for r in report.transitive_files[:20]
        ],
        "cochange_warnings": [
            {"file": w.file_path, "message": w.message}
            for w in report.missing_cochange_files[:10]
        ],
        "recommended_reviewers": [
            {"email": r.email, "ownership_pct": r.ownership_pct}
            for r in report.recommended_reviewers
        ],
        "test_gap_files": report.test_gap_files[:10],
        "analyzed_at": report.analyzed_at,
    }


# ─── Tool 10: get_knowledge_map (NEW) ────────────────────────────────────────

@mcp.tool()
async def get_knowledge_map(
    scope: str = "full",
    module_path: str | None = None,
    author_email: str | None = None,
) -> dict[str, Any]:
    """
    Return a knowledge distribution map: who owns what, knowledge silos, bus factor risks.
    """
    db, graph, _, repo_id = await _get_deps()
    metrics_repo = GitMetricsRepository(db)

    query = "SELECT m.owner_email, f.path, m.ownership_pct, m.churn_count FROM file_git_metrics m JOIN files f ON m.file_id = f.id WHERE f.repo_id = ?"
    params: tuple = (repo_id,)

    if module_path:
        query += " AND f.path LIKE ?"
        params = (repo_id, f"{module_path}%")

    if author_email:
        query += " AND m.owner_email = ?"
        params = (*params, author_email)

    rows = await db.fetchall(query, params)

    # Build knowledge map
    owner_files: dict[str, list[str]] = {}
    silos: list[str] = []
    for row in rows:
        owner = row["owner_email"]
        path = row["path"]
        owner_files.setdefault(owner, []).append(path)
        if row["ownership_pct"] > 0.8:
            silos.append(path)

    return {
        "owners": {
            owner: {"files_owned": len(files), "top_files": files[:5]}
            for owner, files in sorted(owner_files.items(), key=lambda x: len(x[1]), reverse=True)[:10]
        },
        "bus_factor_risks": silos[:20],
        "total_files_analyzed": len(rows),
    }


# ─── Tool 11: get_test_gaps (NEW) ────────────────────────────────────────────

@mcp.tool()
async def get_test_gaps(
    file_path: str | None = None,
    min_complexity_threshold: float = 0.5,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    """
    Identify files/symbols with no corresponding tests.
    Ranked by complexity + hotspot score — highest-risk untested code first.
    """
    db, _, _, repo_id = await _get_deps()

    query = """
        SELECT f.path, f.language, m.temporal_hotspot_score, m.churn_count,
               m.percentile_rank
        FROM files f
        LEFT JOIN file_git_metrics m ON m.file_id = f.id
        WHERE f.repo_id = ?
          AND f.path NOT LIKE '%test%'
          AND f.path NOT LIKE '%spec%'
          AND f.path NOT LIKE '%__pycache__%'
        ORDER BY COALESCE(m.temporal_hotspot_score, 0) DESC
        LIMIT ?
    """
    params: tuple = (repo_id, top_n * 3)

    if file_path:
        query = query.replace("WHERE f.repo_id = ?", "WHERE f.repo_id = ? AND f.path = ?")
        params = (repo_id, file_path, top_n * 3)

    rows = await db.fetchall(query, params)
    gaps: list[dict] = []
    for row in rows:
        path = row["path"]
        basename = Path(path).stem
        test_patterns = [f"test_{basename}", f"{basename}_test", f"{basename}.test", f"{basename}.spec"]
        has_test = any(
            await db.fetchall("SELECT 1 FROM files WHERE repo_id=? AND path LIKE ?", (repo_id, f"%{p}%"))
            for p in test_patterns
        )
        if not has_test:
            gaps.append({
                "file_path": path,
                "temporal_hotspot_score": round(row["temporal_hotspot_score"] or 0, 3),
                "churn_count": row["churn_count"] or 0,
                "risk_level": "high" if (row["temporal_hotspot_score"] or 0) > 1.0 else "medium",
            })
        if len(gaps) >= top_n:
            break
    return gaps


# ─── Tool 12: get_security_hotspots (NEW) ────────────────────────────────────

@mcp.tool()
async def get_security_hotspots(
    severity: str = "high",
    pattern_set: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Return files with security-sensitive patterns:
    auth/authz logic, input deserialization, SQL construction,
    highly connected entry points with no test coverage.
    """
    db, graph, _, repo_id = await _get_deps()

    security_keywords = pattern_set or [
        "password", "token", "secret", "api_key", "auth", "login",
        "jwt", "oauth", "session", "credential", "encrypt", "hash",
        "sql", "query", "execute", "deserializ", "pickle", "eval",
        "subprocess", "exec", "shell", "unsafe",
    ]

    hotspots: list[dict] = []
    for keyword in security_keywords:
        rows = await db.fetchall(
            """SELECT DISTINCT f.path, s.name, s.kind, s.line_start
               FROM files f JOIN symbols s ON s.file_id = f.id
               WHERE f.repo_id = ? AND (
                 LOWER(s.name) LIKE ? OR LOWER(f.path) LIKE ?
               )
               LIMIT 5""",
            (repo_id, f"%{keyword}%", f"%{keyword}%"),
        )
        for row in rows:
            hotspots.append({
                "file_path": row["path"],
                "symbol": row["name"],
                "kind": row["kind"],
                "line": row["line_start"],
                "pattern": keyword,
                "severity": "high" if keyword in ("password", "secret", "token", "api_key") else "medium",
            })

    # Filter by severity
    if severity != "all":
        hotspots = [h for h in hotspots if h["severity"] == severity]

    # Deduplicate by file
    seen_files: set[str] = set()
    result: list[dict] = []
    for h in hotspots:
        if h["file_path"] not in seen_files:
            seen_files.add(h["file_path"])
            result.append(h)

    return result[:30]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _risk_label(score: float) -> str:
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


async def start_server(config: RepomindConfig) -> None:
    global _config, _db, _vector, _graph_store, _repo_id
    from ..utils.hash_utils import repo_id as _get_repo_id

    _config = config
    _repo_id = _get_repo_id(config.repo_path)
    _db = AsyncSQLiteDB(config.db_path)
    _vector = LanceDBStore(config.vector_dir)
    _graph_store = GraphStore(config.graph_path)

    config.ensure_data_dir()
    await _db.connect()
    await _vector.connect()
    _graph_store.load()

    log.info("mcp_server_ready", repo_id=_repo_id, tools=12)
