from __future__ import annotations

import json
import re
from pathlib import Path

from .base import DynamicEdge, DynamicHintExtractor
from ...utils.logging import get_logger

log = get_logger(__name__)


class NodeDynamicHints(DynamicHintExtractor):
    """
    Recovers edges invisible to static analysis in Node/TypeScript projects:
    - package.json "main" / "module" entry points
    - tsconfig.json path aliases
    - jest.config test patterns
    """
    name = "node_package"

    def extract(self, repo_root: Path) -> list[DynamicEdge]:
        edges: list[DynamicEdge] = []
        edges.extend(self._parse_package_json(repo_root))
        edges.extend(self._parse_tsconfig(repo_root))
        return edges

    def _parse_package_json(self, repo_root: Path) -> list[DynamicEdge]:
        edges: list[DynamicEdge] = []
        pkg = repo_root / "package.json"
        if not pkg.exists():
            return edges
        try:
            data = json.loads(pkg.read_text())
            pkg_str = str(pkg)
            for field in ("main", "module", "browser", "exports"):
                val = data.get(field)
                if isinstance(val, str):
                    target = repo_root / val
                    if target.exists():
                        edges.append(DynamicEdge(
                            source=pkg_str,
                            target=str(target),
                            edge_type="dynamic_imports",
                            hint_source=self.name,
                        ))
            for script_name, script_val in data.get("scripts", {}).items():
                # Extract file paths from common script patterns
                for m in re.finditer(r'(?:node|ts-node|tsx)\s+([\w./]+\.(?:js|ts|mjs))', script_val):
                    target = repo_root / m.group(1)
                    if target.exists():
                        edges.append(DynamicEdge(
                            source=pkg_str,
                            target=str(target),
                            edge_type="dynamic_uses",
                            hint_source=self.name,
                        ))
        except Exception:
            pass
        return edges

    def _parse_tsconfig(self, repo_root: Path) -> list[DynamicEdge]:
        """Parse tsconfig.json path aliases to resolve imports correctly."""
        edges: list[DynamicEdge] = []
        for tsconfig in repo_root.rglob("tsconfig*.json"):
            if "node_modules" in str(tsconfig):
                continue
            try:
                content = re.sub(r"//.*", "", tsconfig.read_text())  # strip comments
                data = json.loads(content)
                paths = data.get("compilerOptions", {}).get("paths", {})
                base_url = data.get("compilerOptions", {}).get("baseUrl", ".")
                base = (tsconfig.parent / base_url).resolve()
                for alias, targets in paths.items():
                    for t in targets:
                        t_clean = t.replace("/*", "")
                        resolved = base / t_clean
                        if resolved.exists():
                            edges.append(DynamicEdge(
                                source=str(tsconfig),
                                target=str(resolved),
                                edge_type="dynamic_imports",
                                hint_source=f"{self.name}_alias:{alias}",
                            ))
            except Exception:
                pass
        return edges
