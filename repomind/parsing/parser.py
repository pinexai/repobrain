from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .languages import get_handler
from .symbols import ParseResult
from ..utils.logging import get_logger

log = get_logger(__name__)


def _parse_file_worker(file_path: str, language: str) -> ParseResult:
    """Top-level function for ProcessPoolExecutor (must be picklable)."""
    handler = get_handler(language)
    if handler is None:
        return ParseResult(file_path=file_path, language=language, error="no handler")
    path = Path(file_path)
    try:
        content = path.read_text(errors="replace")
        return handler.parse(path, content)
    except Exception as e:
        return ParseResult(file_path=file_path, language=language, error=str(e))


class AsyncTreeSitterParser:
    """
    Async wrapper that offloads tree-sitter parsing to a ProcessPoolExecutor.
    tree-sitter is CPU-bound and releases the GIL, so processes > threads here.
    """

    def __init__(self, workers: int = 4) -> None:
        self._workers = workers
        self._executor: ProcessPoolExecutor | None = None

    def start(self) -> None:
        self._executor = ProcessPoolExecutor(max_workers=self._workers)

    def stop(self) -> None:
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    async def parse(self, file_path: Path, language: str) -> ParseResult:
        loop = asyncio.get_event_loop()
        if self._executor is None:
            self.start()
        try:
            return await loop.run_in_executor(
                self._executor,
                _parse_file_worker,
                str(file_path),
                language,
            )
        except Exception as e:
            log.warning("parse_error", file=str(file_path), error=str(e))
            return ParseResult(file_path=str(file_path), language=language, error=str(e))

    async def parse_batch(
        self,
        files: list[tuple[Path, str]],
        concurrency: int = 20,
    ) -> list[ParseResult]:
        sem = asyncio.Semaphore(concurrency)

        async def _parse_one(fp: Path, lang: str) -> ParseResult:
            async with sem:
                return await self.parse(fp, lang)

        tasks = [_parse_one(fp, lang) for fp, lang in files]
        return await asyncio.gather(*tasks)
