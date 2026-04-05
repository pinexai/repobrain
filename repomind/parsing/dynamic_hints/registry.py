from __future__ import annotations

from pathlib import Path

from .base import DynamicEdge, DynamicHintExtractor
from .django import DjangoDynamicHints
from .node import NodeDynamicHints
from .pytest import PytestDynamicHints
from ...utils.logging import get_logger

log = get_logger(__name__)

_ALL_EXTRACTORS: list[DynamicHintExtractor] = [
    DjangoDynamicHints(),
    PytestDynamicHints(),
    NodeDynamicHints(),
]


class HintRegistry:
    def __init__(self, extractors: list[DynamicHintExtractor] | None = None) -> None:
        self._extractors = extractors or _ALL_EXTRACTORS

    def extract_all(self, repo_root: Path) -> list[DynamicEdge]:
        all_edges: list[DynamicEdge] = []
        for extractor in self._extractors:
            try:
                edges = extractor.extract(repo_root)
                all_edges.extend(edges)
                log.info(
                    "dynamic_hints_extracted",
                    extractor=extractor.name,
                    edges=len(edges),
                )
            except Exception as e:
                log.warning("hint_extractor_failed", extractor=extractor.name, error=str(e))
        return all_edges
