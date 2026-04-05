from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    kind: str  # "function" | "class" | "method" | "variable" | "constant"
    line_start: int
    line_end: int
    visibility: str = "public"  # "public" | "private" | "protected"
    signature: str | None = None


@dataclass
class Import:
    source: str          # e.g. "os.path", "./utils", "../config"
    names: list[str]     # e.g. ["join", "exists"] or ["*"] or []
    is_dynamic: bool = False
    hint_source: str | None = None  # e.g. "django_settings", "pytest_conftest"
    resolved_path: str | None = None


@dataclass
class ParseResult:
    file_path: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.error is None
