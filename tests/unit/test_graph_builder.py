from __future__ import annotations

from pathlib import Path

import pytest

from repomind.graph.builder import CodeGraphBuilder
from repomind.parsing.symbols import Import, ParseResult, Symbol
from repomind.storage.graph import GraphStore


@pytest.fixture
def setup(tmp_path: Path):
    graph = GraphStore(tmp_path / "graph.graphml")
    builder = CodeGraphBuilder(graph, tmp_path)
    return graph, builder, tmp_path


class TestCodeGraphBuilder:
    def test_add_file_creates_node(self, setup):
        graph, builder, root = setup
        pr = ParseResult(
            file_path="src/main.py",
            language="python",
            symbols=[],
            imports=[],
        )
        builder.add_file(pr)
        assert graph.has_node("src/main.py")

    def test_add_file_stores_language(self, setup):
        graph, builder, root = setup
        pr = ParseResult(
            file_path="src/main.py",
            language="python",
            symbols=[],
            imports=[],
        )
        builder.add_file(pr)
        attrs = graph.get_node_attrs("src/main.py")
        assert attrs["language"] == "python"

    def test_add_file_stores_symbol_count(self, setup):
        graph, builder, root = setup
        sym = Symbol(name="MyClass", kind="class", start_line=1, end_line=10)
        pr = ParseResult(
            file_path="src/main.py",
            language="python",
            symbols=[sym],
            imports=[],
        )
        builder.add_file(pr, centrality=0.5, hotspot_score=3.0)
        attrs = graph.get_node_attrs("src/main.py")
        assert attrs["symbol_count"] == 1
        assert attrs["centrality"] == 0.5

    def test_add_imports_creates_edge_for_relative_import(self, setup):
        graph, builder, root = setup
        # Create the target file so resolution succeeds
        (root / "src").mkdir()
        (root / "src" / "utils.py").write_text("# utils")

        pr = ParseResult(
            file_path=str(root / "src" / "main.py"),
            language="python",
            symbols=[],
            imports=[Import(source="./utils", is_dynamic=False)],
        )
        builder.add_file(pr)
        builder.add_imports(pr)
        target = str(root / "src" / "utils.py")
        assert graph.has_node(pr.file_path)

    def test_add_dynamic_edges_skips_missing_nodes(self, setup):
        from repomind.parsing.dynamic_hints import DynamicEdge
        graph, builder, root = setup
        # Neither node exists — should not crash, edge silently skipped
        edges = [DynamicEdge(source="a.py", target="b.py", edge_type="uses", hint_source="test")]
        builder.add_dynamic_edges(edges)
        assert not graph.has_node("a.py")

    def test_add_dynamic_edges_adds_when_nodes_exist(self, setup):
        from repomind.parsing.dynamic_hints import DynamicEdge
        graph, builder, root = setup
        graph.add_node("a.py")
        graph.add_node("b.py")
        edges = [DynamicEdge(source="a.py", target="b.py", edge_type="uses", hint_source="pytest")]
        builder.add_dynamic_edges(edges)
        assert "b.py" in graph.successors("a.py")

    def test_get_direct_dependencies(self, setup):
        graph, builder, root = setup
        graph.add_node("a.py")
        graph.add_node("b.py")
        graph.add_edge("a.py", "b.py")
        assert "b.py" in builder.get_direct_dependencies("a.py")

    def test_get_reverse_dependencies(self, setup):
        graph, builder, root = setup
        graph.add_node("a.py")
        graph.add_node("b.py")
        graph.add_edge("a.py", "b.py")
        assert "a.py" in builder.get_reverse_dependencies("b.py")
