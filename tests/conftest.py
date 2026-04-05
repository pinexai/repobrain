from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a minimal fake Python repo for testing."""
    # main.py
    (tmp_path / "main.py").write_text("""
from utils.helpers import greet
from config import Settings

def main():
    settings = Settings()
    print(greet(settings.name))

if __name__ == "__main__":
    main()
""")
    # utils/helpers.py
    (tmp_path / "utils").mkdir()
    (tmp_path / "utils/__init__.py").write_text("")
    (tmp_path / "utils/helpers.py").write_text("""
def greet(name: str) -> str:
    return f"Hello, {name}!"

def farewell(name: str) -> str:
    return f"Goodbye, {name}!"
""")
    # config.py
    (tmp_path / "config.py").write_text("""
class Settings:
    name: str = "World"
    debug: bool = False
""")
    # test_helpers.py
    (tmp_path / "test_helpers.py").write_text("""
from utils.helpers import greet, farewell

def test_greet():
    assert greet("Alice") == "Hello, Alice!"

def test_farewell():
    assert farewell("Bob") == "Goodbye, Bob!"
""")
    return tmp_path


@pytest.fixture
def tmp_db(tmp_path: Path):
    from repomind.storage.sql import AsyncSQLiteDB
    return AsyncSQLiteDB(tmp_path / "test.db")
