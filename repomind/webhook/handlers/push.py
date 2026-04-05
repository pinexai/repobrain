from __future__ import annotations

import asyncio
from pathlib import Path

from ...config import RepomindConfig
from ...utils.logging import get_logger

log = get_logger(__name__)


class PushEventHandler:
    def __init__(self, config: RepomindConfig) -> None:
        self._config = config
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    async def handle(self, payload: dict) -> None:
        """Extract changed files and enqueue incremental re-index."""
        changed: list[str] = []
        for commit in payload.get("commits", []):
            changed.extend(commit.get("modified", []))
            changed.extend(commit.get("added", []))
        changed = list(set(changed))

        if changed:
            log.info("push_event", changed_files=len(changed))
            await self._queue.put(changed)
            if self._worker_task is None or self._worker_task.done():
                self._worker_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self) -> None:
        """Debounced worker: waits 5s then processes accumulated changes."""
        await asyncio.sleep(5)
        all_changed: list[str] = []
        while not self._queue.empty():
            all_changed.extend(await self._queue.get())

        if all_changed:
            log.info("incremental_reindex_start", files=len(all_changed))
            try:
                from ...core.indexer import AsyncIndexingPipeline
                pipeline = AsyncIndexingPipeline(self._config)
                await pipeline.run(incremental=True)
            except Exception as e:
                log.error("incremental_reindex_failed", error=str(e))
