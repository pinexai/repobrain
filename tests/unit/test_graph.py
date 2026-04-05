from __future__ import annotations

from pathlib import Path

import pytest

from repomind.storage.graph import GraphStore
from repomind.graph.builder import CodeGraphBuilder
from repomind.graph.analyzer import GraphAnalyzer
from repomind.parsing.symbols import Import, ParseResult, Symbol


@pytest.fixture
def graph(tmp_path: Path) -> GraphStore:
    return GraphStore(tmp_path / "graph.graphml")


@pytest.fixture
def builder(graph: GraphStore, tmp_path: Path) -> CodeGraphBuilder:
    return CodeGraphBuilder(graph, tmp_path)


class TestGraphStore:
    def test_add_and_retrieve_node(self, graph: GraphStore):
        graph.add_node("a.py", type="file", language="python")
        assert graph.has_node("a.py")
        attrs = graph.get_node_attrs("a.py")
        assert attrs["language"] == "python"

    def test_add_edge_and_traverse(self, graph: GraphStore):
        graph.add_node("a.py")
        graph.add_node("b.py")
        graph.add_edge("a.py", "b.py", type="imports")
        assert "b.py" in graph.successors("a.py")
        assert "a.py" in graph.predecessors("b.py")

    def test_ancestors(self, graph: GraphStore):
        graph.add_node("a.py")
        graph.add_node("b.py")
        graph.add_node("c.py")
        graph.add_edge("a.py", "b.py")
        graph.add_edge("b.py", "c.py")
        # c.py is depended on by a.py (transitively)
        ancestors = graph.ancestors("c.py")
        assert "a.py" in ancestors
        assert "b.py" in ancestors

    def test_dead_code_detection(self, graph: GraphStore):
        graph.add_node("main.py")
        graph.add_node("utils.py")
        graph.add_node("dead.py")  # not reachable from main
        graph.add_edge("main.py", "utils.py")

        dead = graph.find_dead_code(["main.py"])
        assert "dead.py" in dead
        assert "utils.py" not in dead

    def test_pagerank(self, graph: GraphStore):
        for node in ["a.py", "b.py", "c.py"]:
            graph.add_node(node)
        graph.add_edge("a.py", "c.py")
        graph.add_edge("b.py", "c.py")
        pr = graph.pagerank()
        # c.py should have highest pagerank (2 incoming edges)
        assert pr["c.py"] > pr["a.py"]

    def test_save_and_load(self, tmp_path: Path):
        path = tmp_path / "graph.graphml"
        g1 = GraphStore(path)
        g1.add_node("a.py", language="python")
        g1.add_node("b.py", language="go")
        g1.add_edge("a.py", "b.py")
        g1.save()

        g2 = GraphStore(path)
        g2.load()
        assert g2.has_node("a.py")
        assert "b.py" in g2.successors("a.py")
