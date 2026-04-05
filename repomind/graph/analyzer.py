from __future__ import annotations

from ..storage.graph import GraphStore
from ..utils.logging import get_logger

log = get_logger(__name__)


class GraphAnalyzer:
    """
    Computes graph metrics: PageRank, community detection, centrality.
    Results are used to enrich node attributes and score hotspots.
    """

    def __init__(self, graph_store: GraphStore) -> None:
        self._store = graph_store

    def compute_pagerank(self) -> dict[str, float]:
        log.info("computing_pagerank", nodes=self._store.node_count())
        return self._store.pagerank()

    def compute_communities(self) -> dict[str, int]:
        """Returns {node_id: community_id}."""
        communities = self._store.communities()
        result: dict[str, int] = {}
        for idx, community in enumerate(communities):
            for node in community:
                result[node] = idx
        return result

    def compute_betweenness(self) -> dict[str, float]:
        log.info("computing_betweenness", nodes=self._store.node_count())
        return self._store.betweenness_centrality()

    def find_dead_code(self, entry_points: list[str]) -> list[str]:
        return self._store.find_dead_code(entry_points)

    def find_entry_points(self) -> list[str]:
        """Heuristic: files with no in-edges (nothing imports them) + common entry names."""
        g = self._store.graph
        entry_points = []
        common_names = {"main", "index", "app", "server", "cli", "manage", "__main__"}

        for node in g.nodes():
            if g.in_degree(node) == 0:
                entry_points.append(node)
            else:
                import os
                basename = os.path.splitext(os.path.basename(node))[0]
                if basename in common_names:
                    entry_points.append(node)

        return list(set(entry_points))

    def get_dependency_path(self, source: str, target: str) -> list[str] | None:
        return self._store.shortest_path(source, target)

    def get_transitive_dependents(self, file_path: str, max_depth: int = 5) -> set[str]:
        """All files that (transitively) depend on file_path."""
        return self._store.ancestors(file_path)

    def get_module_subgraph(self, module_path: str) -> list[str]:
        """Return all files within a module directory."""
        return [n for n in self._store.graph.nodes() if n.startswith(module_path)]
