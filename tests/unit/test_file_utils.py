from __future__ import annotations

from pathlib import Path

import pytest

from repomind.utils.hash_utils import content_hash, repo_id, string_hash


class TestContentHash:
    def test_deterministic(self, tmp_path: Path):
        f = tmp_path / "file.py"
        f.write_text("hello world")
        h1 = content_hash(f)
        h2 = content_hash(f)
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path: Path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("hello")
        f2.write_text("world")
        assert content_hash(f1) != content_hash(f2)

    def test_returns_hex_string(self, tmp_path: Path):
        f = tmp_path / "file.py"
        f.write_bytes(b"\x00\xff\xab")
        h = content_hash(f)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex = 64 chars
        int(h, 16)  # must be valid hex


class TestRepoId:
    def test_stable_for_same_path(self, tmp_path: Path):
        assert repo_id(tmp_path) == repo_id(tmp_path)

    def test_different_for_different_paths(self, tmp_path: Path):
        p1 = tmp_path / "repo1"
        p2 = tmp_path / "repo2"
        p1.mkdir()
        p2.mkdir()
        assert repo_id(p1) != repo_id(p2)

    def test_returns_16_char_string(self, tmp_path: Path):
        rid = repo_id(tmp_path)
        assert isinstance(rid, str)
        assert len(rid) == 16


class TestStringHash:
    def test_deterministic(self):
        assert string_hash("hello") == string_hash("hello")

    def test_different_strings(self):
        assert string_hash("a") != string_hash("b")

    def test_empty_string(self):
        h = string_hash("")
        assert isinstance(h, str)
        assert len(h) == 64
