from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DynamicEdge:
    source: str      # file path
    target: str      # file path
    edge_type: str   # "dynamic_uses" | "dynamic_imports" | "url_route"
    hint_source: str # e.g. "django_settings", "pytest_conftest"
    weight: float = 1.0


class DynamicHintExtractor(ABC):
    name: str = ""

    @abstractmethod
    def extract(self, repo_root: Path) -> list[DynamicEdge]:
        """Analyze framework-specific files and return inferred edges."""
