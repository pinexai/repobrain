from __future__ import annotations

import fnmatch
import re
from pathlib import Path

LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
}

BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".wasm",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".pyc", ".pyo", ".class", ".o", ".a",
    ".db", ".sqlite", ".sqlite3",
    ".ttf", ".otf", ".woff", ".woff2",
    ".lock", ".sum",
})

_BINARY_SNIFF_BYTES = 8192
_NULL_THRESHOLD = 0.01


def detect_language(path: Path) -> str | None:
    return LANGUAGE_MAP.get(path.suffix.lower())


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        chunk = path.read_bytes()[:_BINARY_SNIFF_BYTES]
        null_count = chunk.count(b"\x00")
        return null_count / max(len(chunk), 1) > _NULL_THRESHOLD
    except OSError:
        return True


def walk_repo(
    root: Path,
    exclude_patterns: list[str],
    languages: list[str],
    max_file_size_bytes: int,
) -> list[Path]:
    """Walk repo respecting .gitignore-style excludes and size limits."""
    gitignore_patterns = _load_gitignore(root)
    all_excludes = exclude_patterns + gitignore_patterns
    results: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_str = str(rel)

        if _matches_any(rel_str, all_excludes):
            continue

        lang = detect_language(path)
        if lang is None:
            continue
        if languages and lang not in languages:
            continue
        if is_binary(path):
            continue
        try:
            if path.stat().st_size > max_file_size_bytes:
                continue
        except OSError:
            continue

        results.append(path)

    return results


def _matches_any(rel_str: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel_str, pat):
            return True
        # Also match against path components for patterns like "**/node_modules/**"
        normalized = pat.replace("**/", "").replace("/**", "")
        if normalized and normalized in rel_str:
            return True
    return False


def _load_gitignore(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns: list[str] = []
    for line in gitignore.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def find_files_by_name(root: Path, name: str) -> list[Path]:
    return list(root.rglob(name))


def relative_import_to_path(
    base_file: Path,
    import_str: str,
    root: Path,
) -> Path | None:
    """Resolve a relative import string to an absolute path."""
    parts = import_str.replace(".", "/").split("/")
    candidate = base_file.parent / Path(*parts)
    for suffix in [".py", ".ts", ".js", "/index.ts", "/index.js"]:
        p = candidate.with_suffix("") if candidate.suffix else candidate
        p = Path(str(p) + suffix)
        if p.exists():
            return p
    return None
