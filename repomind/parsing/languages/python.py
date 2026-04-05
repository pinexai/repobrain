from __future__ import annotations

import re
from pathlib import Path

from ..symbols import Import, ParseResult, Symbol
from .base import LanguageHandler

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    _PY_LANGUAGE = Language(tspython.language())
    _PARSER_AVAILABLE = True
except Exception:
    _PARSER_AVAILABLE = False


class PythonHandler(LanguageHandler):
    language_name = "python"

    def __init__(self) -> None:
        if _PARSER_AVAILABLE:
            self._parser = Parser(_PY_LANGUAGE)

    def parse(self, file_path: Path, content: str) -> ParseResult:
        result = ParseResult(file_path=str(file_path), language="python")

        if not _PARSER_AVAILABLE:
            return self._fallback_parse(file_path, content, result)

        try:
            tree = self._parser.parse(content.encode())
            self._extract_symbols(tree.root_node, content, result)
            self._extract_imports(tree.root_node, content, result)
        except Exception as e:
            result.error = str(e)
            return self._fallback_parse(file_path, content, result)

        return result

    def _extract_symbols(self, root, content: str, result: ParseResult) -> None:
        lines = content.splitlines()

        def visit(node) -> None:  # type: ignore[no-untyped-def]
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    params_node = node.child_by_field_name("parameters")
                    sig = name
                    if params_node:
                        sig += content[params_node.start_byte:params_node.end_byte]
                    result.symbols.append(Symbol(
                        name=name,
                        kind="function",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        visibility=self._visibility(name),
                        signature=sig,
                    ))
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    result.symbols.append(Symbol(
                        name=name,
                        kind="class",
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        visibility=self._visibility(name),
                    ))
                    # Extract methods inside class
                    for child in node.children:
                        if child.type == "block":
                            for stmt in child.children:
                                if stmt.type == "function_definition":
                                    mname_node = stmt.child_by_field_name("name")
                                    if mname_node:
                                        mname = content[mname_node.start_byte:mname_node.end_byte]
                                        result.symbols.append(Symbol(
                                            name=f"{name}.{mname}",
                                            kind="method",
                                            line_start=stmt.start_point[0] + 1,
                                            line_end=stmt.end_point[0] + 1,
                                            visibility=self._visibility(mname),
                                        ))

            for child in node.children:
                visit(child)

        visit(root)

    def _extract_imports(self, root, content: str, result: ParseResult) -> None:
        def visit(node) -> None:  # type: ignore[no-untyped-def]
            if node.type == "import_statement":
                # import os, sys
                for child in node.children:
                    if child.type in ("dotted_name", "aliased_import"):
                        name = content[child.start_byte:child.end_byte].split(" as ")[0].strip()
                        result.imports.append(Import(source=name, names=[]))
            elif node.type == "import_from_statement":
                # from os.path import join, exists
                module_node = node.child_by_field_name("module_name")
                module = content[module_node.start_byte:module_node.end_byte] if module_node else ""
                names: list[str] = []
                for child in node.children:
                    if child.type in ("import_prefix", "module_name"):
                        continue
                    if child.type == "wildcard_import":
                        names = ["*"]
                    elif child.type == "dotted_name":
                        names.append(content[child.start_byte:child.end_byte])
                    elif child.type == "aliased_import":
                        nm = content[child.start_byte:child.end_byte].split(" as ")[0].strip()
                        names.append(nm)
                result.imports.append(Import(source=module, names=names))
            elif node.type == "call":
                # Dynamic: __import__("x") or importlib.import_module("x")
                func_node = node.child_by_field_name("function")
                if func_node:
                    func_text = content[func_node.start_byte:func_node.end_byte]
                    if "import_module" in func_text or func_text == "__import__":
                        args_node = node.child_by_field_name("arguments")
                        if args_node and args_node.child_count > 0:
                            first = args_node.children[0]
                            mod = content[first.start_byte:first.end_byte].strip("\"'")
                            result.imports.append(Import(source=mod, names=[], is_dynamic=True))

            for child in node.children:
                visit(child)

        visit(root)

    def _fallback_parse(self, file_path: Path, content: str, result: ParseResult) -> ParseResult:
        """Regex-based fallback when tree-sitter unavailable."""
        for m in re.finditer(r"^(?:async )?def\s+(\w+)\s*\(", content, re.MULTILINE):
            result.symbols.append(Symbol(
                name=m.group(1),
                kind="function",
                line_start=content[:m.start()].count("\n") + 1,
                line_end=content[:m.start()].count("\n") + 1,
                visibility=self._visibility(m.group(1)),
            ))
        for m in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
            result.symbols.append(Symbol(
                name=m.group(1),
                kind="class",
                line_start=content[:m.start()].count("\n") + 1,
                line_end=content[:m.start()].count("\n") + 1,
            ))
        for m in re.finditer(r"^import\s+([\w., ]+)", content, re.MULTILINE):
            for mod in m.group(1).split(","):
                result.imports.append(Import(source=mod.strip().split(" as ")[0], names=[]))
        for m in re.finditer(r"^from\s+([\w.]+)\s+import\s+([\w, *]+)", content, re.MULTILINE):
            names = [n.strip() for n in m.group(2).split(",")]
            result.imports.append(Import(source=m.group(1), names=names))
        result.error = None
        return result
