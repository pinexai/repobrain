from __future__ import annotations

import re
from pathlib import Path

from ..symbols import Import, ParseResult, Symbol
from .base import LanguageHandler

try:
    import tree_sitter_go as tsgo
    from tree_sitter import Language, Parser

    _GO_LANGUAGE = Language(tsgo.language())
    _PARSER_AVAILABLE = True
except Exception:
    _PARSER_AVAILABLE = False


class GoHandler(LanguageHandler):
    language_name = "go"

    def __init__(self) -> None:
        if _PARSER_AVAILABLE:
            self._parser = Parser(_GO_LANGUAGE)

    def parse(self, file_path: Path, content: str) -> ParseResult:
        result = ParseResult(file_path=str(file_path), language="go")
        try:
            if _PARSER_AVAILABLE:
                tree = self._parser.parse(content.encode())
                self._extract(tree.root_node, content, result)
            else:
                self._fallback(content, result)
        except Exception as e:
            result.error = str(e)
            self._fallback(content, result)
        return result

    def _extract(self, root, content: str, result: ParseResult) -> None:
        def visit(node) -> None:  # type: ignore[no-untyped-def]
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    result.symbols.append(Symbol(
                        name=name, kind="function",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        visibility="public" if name[0].isupper() else "private",
                    ))
            elif node.type == "type_declaration":
                for child in node.children:
                    if child.type == "type_spec":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            name = content[name_node.start_byte:name_node.end_byte]
                            result.symbols.append(Symbol(
                                name=name, kind="class",
                                line_start=node.start_point[0] + 1,
                                line_end=node.end_point[0] + 1,
                                visibility="public" if name[0].isupper() else "private",
                            ))
            elif node.type == "import_declaration":
                for child in node.children:
                    if child.type == "import_spec":
                        path_node = child.child_by_field_name("path")
                        if path_node:
                            src = content[path_node.start_byte:path_node.end_byte].strip("\"")
                            result.imports.append(Import(source=src, names=[]))
            for child in node.children:
                visit(child)

        visit(root)

    def _fallback(self, content: str, result: ParseResult) -> None:
        for m in re.finditer(r"^func\s+(?:\([^)]+\)\s+)?(\w+)", content, re.MULTILINE):
            result.symbols.append(Symbol(
                name=m.group(1), kind="function",
                line_start=content[:m.start()].count("\n") + 1,
                line_end=content[:m.start()].count("\n") + 1,
                visibility="public" if m.group(1)[0].isupper() else "private",
            ))
        for m in re.finditer(r'^import\s+"([^"]+)"', content, re.MULTILINE):
            result.imports.append(Import(source=m.group(1), names=[]))
