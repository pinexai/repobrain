from __future__ import annotations

import hashlib
from pathlib import Path


def content_hash(path: Path) -> str:
    """SHA-256 of file content. Used for change detection."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def string_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def repo_id(repo_path: Path) -> str:
    """Stable ID for a repo based on its absolute path."""
    return hashlib.sha256(str(repo_path.resolve()).encode()).hexdigest()[:16]
