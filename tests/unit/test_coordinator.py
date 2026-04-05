from __future__ import annotations

from pathlib import Path

import pytest

from repomind.core.coordinator import AtomicStorageCoordinator
from repomind.storage.graph import GraphStore
from repomind.storage.sql import AsyncSQLiteDB
from repomind.storage.vector import LanceDBStore


@pytest.fixture
async def coordinator(tmp_path: Path):
    db = AsyncSQLiteDB(tmp_path / "test.db")
    vector = LanceDBStore(tmp_path / "vectors")
    graph = GraphStore(tmp_path / "graph.graphml")
    await db.connect()
    await vector.connect()
    coord = AtomicStorageCoordinator(db, vector, graph)
    yield coord
    await db.close()


class TestAtomicStorageCoordinator:
    async def test_graph_nodes_added_on_success(self, coordinator: AtomicStorageCoordinator):
        async with coordinator.transaction() as txn:
            txn.pending_nodes.append(("src/main.py", {"type": "file", "language": "python"}))
            txn.pending_edges.append(("src/main.py", "src/utils.py", {"type": "imports"}))
            txn.pending_nodes.append(("src/utils.py", {"type": "file", "language": "python"}))

        assert coordinator._graph.has_node("src/main.py")
        assert coordinator._graph.has_node("src/utils.py")

    async def test_graph_nodes_rolled_back_on_exception(self, coordinator: AtomicStorageCoordinator):
        with pytest.raises(ValueError):
            async with coordinator.transaction() as txn:
                txn.pending_nodes.append(("src/bad.py", {"type": "file"}))
                raise ValueError("simulated error")

        # Node should be cleaned up
        assert not coordinator._graph.has_node("src/bad.py")

    async def test_health_check(self, coordinator: AtomicStorageCoordinator):
        health = await coordinator.health_check("test-repo-id")
        assert "sql_files" in health
        assert "graph_nodes" in health
        assert "consistent" in health

    async def test_multiple_transactions_independent(self, coordinator: AtomicStorageCoordinator):
        async with coordinator.transaction() as txn:
            txn.pending_nodes.append(("a.py", {"type": "file"}))

        async with coordinator.transaction() as txn:
            txn.pending_nodes.append(("b.py", {"type": "file"}))

        assert coordinator._graph.has_node("a.py")
        assert coordinator._graph.has_node("b.py")
