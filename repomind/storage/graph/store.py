from __future__ import annotations

from pathlib import Path

import networkx as nx


class GraphStore:
    """NetworkX directed graph with persistence via GraphML."""

    def __init__(self, graph_path: Path) -> None:
        self._path = graph_path
        self._g: nx.DiGraph = nx.DiGraph()

    def load(self) -> None:
        if self._path.exists():
            self._g = nx.read_graphml(str(self._path))

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(self._g, str(self._path))

    @property
    def graph(self) -> nx.DiGraph:
        return self._g

    def add_node(self, node_id: str, **attrs: object) -> None:
        self._g.add_node(node_id, **attrs)

    def add_edge(self, source: str, target: str, **attrs: object) -> None:
        self._g.add_edge(source, target, **attrs)

    def remove_node(self, node_id: str) -> None:
        if self._g.has_node(node_id):
            self._g.remove_node(node_id)

    def remove_edges_for(self, node_id: str) -> None:
        edges_to_remove = list(self._g.in_edges(node_id)) + list(self._g.out_edges(node_id))
        self._g.remove_edges_from(edges_to_remove)

    def successors(self, node_id: str) -> list[str]:
        return list(self._g.successors(node_id))

    def predecessors(self, node_id: str) -> list[str]:
        return list(self._g.predecessors(node_id))

    def ancestors(self, node_id: str) -> set[str]:
        try:
            return nx.ancestors(self._g, node_id)
        except nx.NetworkXError:
            return set()

    def descendants(self, node_id: str) -> set[str]:
        try:
            return nx.descendants(self._g, node_id)
        except nx.NetworkXError:
            return set()

    def pagerank(self, alpha: float = 0.85) -> dict[str, float]:
        if len(self._g) == 0:
            return {}
        return nx.pagerank(self._g, alpha=alpha)

    def communities(self) -> list[set[str]]:
        undirected = self._g.to_undirected()
        return list(nx.community.louvain_communities(undirected))

    def betweenness_centrality(self) -> dict[str, float]:
        n = len(self._g)
        if n == 0:
            return {}
        if n > 30_000:
            # Approximate for large graphs
            k = min(500, n)
            return nx.betweenness_centrality(self._g, k=k, normalized=True)
        return nx.betweenness_centrality(self._g, normalized=True)

    def find_dead_code(self, entry_points: list[str]) -> list[str]:
        """Return nodes unreachable from any entry point."""
        reachable: set[str] = set(entry_points)
        for ep in entry_points:
            reachable |= self.descendants(ep)
        all_nodes = set(self._g.nodes())
        return sorted(all_nodes - reachable)

    def shortest_path(self, source: str, target: str) -> list[str] | None:
        try:
            return nx.shortest_path(self._g, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def node_count(self) -> int:
        return len(self._g)

    def edge_count(self) -> int:
        return len(self._g.edges())

    def get_node_attrs(self, node_id: str) -> dict:
        return dict(self._g.nodes.get(node_id, {}))

    def has_node(self, node_id: str) -> bool:
        return self._g.has_node(node_id)
