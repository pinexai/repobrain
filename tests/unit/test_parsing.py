from __future__ import annotations

from pathlib import Path

import pytest

from repomind.parsing.languages.python import PythonHandler
from repomind.parsing.languages.typescript import TypeScriptHandler
from repomind.parsing.symbols import ParseResult


class TestPythonHandler:
    def test_parses_functions(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("""
def hello(name: str) -> str:
    return f"Hello {name}"

async def async_fetch(url: str):
    pass

class MyClass:
    def method(self):
        pass
""")
        handler = PythonHandler()
        result = handler.parse(f, f.read_text())
        names = [s.name for s in result.symbols]
        assert "hello" in names
        assert "async_fetch" in names
        assert "MyClass" in names

    def test_parses_imports(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("""
import os
import sys
from pathlib import Path
from typing import Optional, List
""")
        handler = PythonHandler()
        result = handler.parse(f, f.read_text())
        sources = [imp.source for imp in result.imports]
        assert "os" in sources
        assert "pathlib" in sources

    def test_visibility_detection(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("""
def public_func(): pass
def _protected(): pass
def __private(): pass
""")
        handler = PythonHandler()
        result = handler.parse(f, f.read_text())
        vis_map = {s.name: s.visibility for s in result.symbols}
        assert vis_map.get("public_func") == "public"
        assert vis_map.get("_protected") == "protected"
        assert vis_map.get("__private") == "private"

    def test_handles_syntax_error_gracefully(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n    pass")
        handler = PythonHandler()
        result = handler.parse(f, f.read_text())
        # Should not raise, just fallback
        assert isinstance(result, ParseResult)


class TestTypeScriptHandler:
    def test_parses_functions(self, tmp_path: Path):
        f = tmp_path / "test.ts"
        f.write_text("""
export function greet(name: string): string {
    return `Hello, ${name}`;
}

export class UserService {
    private db: Database;
}
""")
        handler = TypeScriptHandler()
        result = handler.parse(f, f.read_text())
        names = [s.name for s in result.symbols]
        assert any("greet" in n for n in names)

    def test_parses_imports(self, tmp_path: Path):
        f = tmp_path / "test.ts"
        f.write_text("""
import { useState, useEffect } from 'react';
import axios from 'axios';
""")
        handler = TypeScriptHandler()
        result = handler.parse(f, f.read_text())
        sources = [imp.source for imp in result.imports]
        assert "react" in sources
        assert "axios" in sources
