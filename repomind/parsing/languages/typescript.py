from __future__ import annotations

import re
from pathlib import Path

from ..symbols import Import, ParseResult, Symbol
from .base import LanguageHandler

try:
    import tree_sitter_typescript as tsts
    from tree_sitter import Language, Parser

    _TS_LANGUAGE = Language(tsts.language_typescript())
    _PARSER_AVAILABLE = True
except Exception:
    _PARSER_AVAILABLE = False


class TypeScriptHandler(LanguageHandler):
    language_name = "typescript"

    def __init__(self) -> None:
        if _PARSER_AVAILABLE:
            self._parser = Parser(_TS_LANGUAGE)

    def parse(self, file_path: Path, content: str) -> ParseResult:
        result = ParseResult(file_path=str(file_path), language="typescript")
        try:
            if _PARSER_AVAILABLE:
                tree = self._parser.parse(content.encode())
                self._extract_from_tree(tree.root_node, content, result)
            else:
                self._fallback_parse(content, result)
        except Exception as e:
            result.error = str(e)
            self._fallback_parse(content, result)
        return result

    def _extract_from_tree(self, root, content: str, result: ParseResult) -> None:
        def visit(node) -> None:  # type: ignore[no-untyped-def]
            t = node.type
            if t in ("function_declaration", "function_expression", "arrow_function"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    result.symbols.append(Symbol(
                        name=name, kind="function",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        visibility="public",
                    ))
            elif t == "class_declaration":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    result.symbols.append(Symbol(
                        name=name, kind="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                    ))
            elif t == "import_statement":
                src_node = node.child_by_field_name("source")
                if src_node:
                    src = content[src_node.start_byte:src_node.end_byte].strip("\"'`")
                    result.imports.append(Import(source=src, names=[]))
            elif t == "export_statement":
                dec = node.child_by_field_name("declaration")
                if dec:
                    name_node = dec.child_by_field_name("name")
                    if name_node:
                        result.exports.append(content[name_node.start_byte:name_node.end_byte])
            for child in node.children:
                visit(child)

        visit(root)

    def _fallback_parse(self, content: str, result: ParseResult) -> None:
        for m in re.finditer(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", content):
            result.symbols.append(Symbol(
                name=m.group(1), kind="function",
                line_start=content[:m.start()].count("\n") + 1,
                line_end=content[:m.start()].count("\n") + 1,
            ))
        for m in re.finditer(r"(?:export\s+)?class\s+(\w+)", content):
            result.symbols.append(Symbol(
                name=m.group(1), kind="class",
                line_start=content[:m.start()].count("\n") + 1,
                line_end=content[:m.start()].count("\n") + 1,
            ))
        for m in re.finditer(r'import\s+.*?from\s+["\']([^"\']+)["\']', content):
            result.imports.append(Import(source=m.group(1), names=[]))
        for m in re.finditer(r'require\(["\']([^"\']+)["\']\)', content):
            result.imports.append(Import(source=m.group(1), names=[], is_dynamic=True))
