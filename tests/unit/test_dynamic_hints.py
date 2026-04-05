from __future__ import annotations

from pathlib import Path

import pytest


class TestDjangoDynamicHints:
    def test_extracts_installed_apps(self, tmp_path: Path):
        from repomind.parsing.dynamic_hints.django import DjangoDynamicHints

        # Create Django-like structure
        (tmp_path / "myapp").mkdir()
        (tmp_path / "myapp" / "__init__.py").write_text("")
        (tmp_path / "settings.py").write_text("""
INSTALLED_APPS = [
    'django.contrib.admin',
    'myapp',
]
ROOT_URLCONF = 'myproject.urls'
""")

        hints = DjangoDynamicHints()
        edges = hints.extract(tmp_path)

        # Should find myapp -> __init__.py edge
        targets = [e.target for e in edges]
        assert any("myapp" in t for t in targets)

    def test_no_crash_on_missing_settings(self, tmp_path: Path):
        from repomind.parsing.dynamic_hints.django import DjangoDynamicHints
        hints = DjangoDynamicHints()
        edges = hints.extract(tmp_path)
        assert isinstance(edges, list)


class TestPytestDynamicHints:
    def test_extracts_fixture_edges(self, tmp_path: Path):
        from repomind.parsing.dynamic_hints.pytest import PytestDynamicHints

        (tmp_path / "conftest.py").write_text("""
import pytest

@pytest.fixture
def my_client():
    return {}

@pytest.fixture
def db_session():
    return None
""")
        (tmp_path / "test_something.py").write_text("""
def test_example(my_client):
    assert my_client is not None
""")

        hints = PytestDynamicHints()
        edges = hints.extract(tmp_path)
        assert len(edges) > 0
        sources = [e.source for e in edges]
        assert any("conftest" in s for s in sources)

    def test_no_edges_when_no_fixture_usage(self, tmp_path: Path):
        from repomind.parsing.dynamic_hints.pytest import PytestDynamicHints

        (tmp_path / "conftest.py").write_text("""
import pytest
@pytest.fixture
def unused_fixture():
    pass
""")
        (tmp_path / "test_no_fixtures.py").write_text("""
def test_simple():
    assert 1 + 1 == 2
""")

        hints = PytestDynamicHints()
        edges = hints.extract(tmp_path)
        assert len(edges) == 0


class TestNodeDynamicHints:
    def test_extracts_package_json_entry(self, tmp_path: Path):
        from repomind.parsing.dynamic_hints.node import NodeDynamicHints

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.js").write_text("console.log('hello')")
        (tmp_path / "package.json").write_text('{"main": "src/index.js"}')

        hints = NodeDynamicHints()
        edges = hints.extract(tmp_path)
        assert len(edges) > 0

    def test_no_crash_on_missing_package_json(self, tmp_path: Path):
        from repomind.parsing.dynamic_hints.node import NodeDynamicHints
        hints = NodeDynamicHints()
        edges = hints.extract(tmp_path)
        assert isinstance(edges, list)
