from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..symbols import ParseResult


class LanguageHandler(ABC):
    """ABC for per-language tree-sitter parsing strategies."""

    language_name: str = ""

    @abstractmethod
    def parse(self, file_path: Path, content: str) -> ParseResult:
        """Parse a file and return symbols + imports."""

    def _visibility(self, name: str) -> str:
        if name.startswith("__") and not name.endswith("__"):
            return "private"
        if name.startswith("_"):
            return "protected"
        return "public"
