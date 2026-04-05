from .base import LanguageHandler
from .go import GoHandler
from .python import PythonHandler
from .typescript import TypeScriptHandler

_HANDLERS: dict[str, LanguageHandler] = {
    "python": PythonHandler(),
    "typescript": TypeScriptHandler(),
    "javascript": TypeScriptHandler(),  # JS reuses TS handler with regex fallback
    "go": GoHandler(),
}


def get_handler(language: str) -> LanguageHandler | None:
    return _HANDLERS.get(language)


__all__ = ["LanguageHandler", "PythonHandler", "TypeScriptHandler", "GoHandler", "get_handler"]
