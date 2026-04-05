from __future__ import annotations

import ast
from pathlib import Path

from .base import DynamicEdge, DynamicHintExtractor
from ...utils.logging import get_logger

log = get_logger(__name__)


class PytestDynamicHints(DynamicHintExtractor):
    """
    Recovers edges from pytest fixtures defined in conftest.py files.
    Without this, test files appear disconnected from their fixture providers.
    """
    name = "pytest_conftest"

    def extract(self, repo_root: Path) -> list[DynamicEdge]:
        edges: list[DynamicEdge] = []
        conftest_files = list(repo_root.rglob("conftest.py"))

        for conftest in conftest_files:
            if ".venv" in str(conftest):
                continue
            fixture_names = self._extract_fixture_names(conftest)
            if not fixture_names:
                continue
            # Find test files in conftest's scope (same dir and below)
            scope_dir = conftest.parent
            for test_file in scope_dir.rglob("test_*.py"):
                if self._uses_any_fixture(test_file, fixture_names):
                    edges.append(DynamicEdge(
                        source=str(conftest),
                        target=str(test_file),
                        edge_type="dynamic_uses",
                        hint_source=self.name,
                    ))

        return edges

    def _extract_fixture_names(self, conftest: Path) -> list[str]:
        names: list[str] = []
        try:
            tree = ast.parse(conftest.read_text(errors="replace"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if (isinstance(decorator, ast.Attribute) and decorator.attr == "fixture") or \
                           (isinstance(decorator, ast.Name) and decorator.id == "fixture") or \
                           (isinstance(decorator, ast.Call) and (
                               (isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "fixture") or
                               (isinstance(decorator.func, ast.Name) and decorator.func.id == "fixture")
                           )):
                            names.append(node.name)
        except Exception:
            pass
        return names

    def _uses_any_fixture(self, test_file: Path, fixture_names: list[str]) -> bool:
        try:
            tree = ast.parse(test_file.read_text(errors="replace"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    param_names = {arg.arg for arg in node.args.args}
                    if param_names & set(fixture_names):
                        return True
        except Exception:
            pass
        return False
