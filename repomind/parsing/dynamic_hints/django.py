from __future__ import annotations

import ast
import re
from pathlib import Path

from .base import DynamicEdge, DynamicHintExtractor
from ...utils.logging import get_logger

log = get_logger(__name__)


class DjangoDynamicHints(DynamicHintExtractor):
    """
    Recovers edges invisible to static analysis in Django projects:
    - INSTALLED_APPS → app module files
    - ROOT_URLCONF → url configuration files
    - MIDDLEWARE → middleware class files
    - AUTH_USER_MODEL → custom user model
    """
    name = "django_settings"

    def extract(self, repo_root: Path) -> list[DynamicEdge]:
        edges: list[DynamicEdge] = []
        settings_files = self._find_settings(repo_root)
        for sf in settings_files:
            edges.extend(self._parse_settings(sf, repo_root))
        edges.extend(self._parse_url_includes(repo_root))
        return edges

    def _find_settings(self, root: Path) -> list[Path]:
        candidates: list[Path] = []
        for p in root.rglob("settings.py"):
            if ".venv" not in str(p) and "node_modules" not in str(p):
                candidates.append(p)
        for p in root.rglob("settings/"):
            if p.is_dir():
                candidates.extend(p.glob("*.py"))
        return candidates

    def _parse_settings(self, settings_file: Path, repo_root: Path) -> list[DynamicEdge]:
        edges: list[DynamicEdge] = []
        try:
            content = settings_file.read_text(errors="replace")
            tree = ast.parse(content)
        except Exception:
            return edges

        settings_path = str(settings_file)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                name = target.id

                if name == "INSTALLED_APPS" and isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            app_path = self._app_label_to_path(elt.value, repo_root)
                            if app_path:
                                edges.append(DynamicEdge(
                                    source=settings_path,
                                    target=str(app_path),
                                    edge_type="dynamic_imports",
                                    hint_source=self.name,
                                ))

                elif name == "ROOT_URLCONF" and isinstance(node.value, ast.Constant):
                    url_path = self._module_to_path(node.value.value, repo_root)
                    if url_path:
                        edges.append(DynamicEdge(
                            source=settings_path,
                            target=str(url_path),
                            edge_type="dynamic_imports",
                            hint_source=self.name,
                        ))

                elif name == "MIDDLEWARE" and isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            mod = ".".join(elt.value.split(".")[:-1])
                            mw_path = self._module_to_path(mod, repo_root)
                            if mw_path:
                                edges.append(DynamicEdge(
                                    source=settings_path,
                                    target=str(mw_path),
                                    edge_type="dynamic_uses",
                                    hint_source=self.name,
                                ))

        return edges

    def _parse_url_includes(self, repo_root: Path) -> list[DynamicEdge]:
        edges: list[DynamicEdge] = []
        for urls_file in repo_root.rglob("urls.py"):
            if ".venv" in str(urls_file):
                continue
            try:
                content = urls_file.read_text(errors="replace")
                for m in re.finditer(r'include\(["\']([^"\']+)["\']', content):
                    included_path = self._module_to_path(m.group(1), repo_root)
                    if included_path:
                        edges.append(DynamicEdge(
                            source=str(urls_file),
                            target=str(included_path),
                            edge_type="url_route",
                            hint_source=self.name,
                        ))
            except Exception:
                pass
        return edges

    def _app_label_to_path(self, app_label: str, repo_root: Path) -> Path | None:
        return self._module_to_path(app_label, repo_root)

    def _module_to_path(self, module: str, repo_root: Path) -> Path | None:
        parts = module.split(".")
        candidate = repo_root / Path(*parts)
        if (candidate / "__init__.py").exists():
            return candidate / "__init__.py"
        if candidate.with_suffix(".py").exists():
            return candidate.with_suffix(".py")
        return None
