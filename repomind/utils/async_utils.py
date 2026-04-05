from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def gather_with_semaphore(
    semaphore: asyncio.Semaphore,
    *coros: Awaitable[T],
) -> list[T]:
    """Run coroutines concurrently, bounded by a semaphore."""
    async def _run(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(*(_run(c) for c in coros))


async def chunked_gather(
    coros: list[Awaitable[T]],
    concurrency: int,
) -> list[T]:
    """Process coroutines in chunks of `concurrency`."""
    sem = asyncio.Semaphore(concurrency)
    return await gather_with_semaphore(sem, *coros)


async def stream_results(
    items: list[T],
    processor: Callable[[T], Awaitable[T]],
    concurrency: int,
) -> AsyncIterator[T]:
    """Process items concurrently and yield results as they complete."""
    sem = asyncio.Semaphore(concurrency)
    queue: asyncio.Queue[T | None] = asyncio.Queue()

    async def _worker(item: T) -> None:
        async with sem:
            result = await processor(item)
            await queue.put(result)

    tasks = [asyncio.create_task(_worker(item)) for item in items]

    async def _finalizer() -> None:
        await asyncio.gather(*tasks, return_exceptions=True)
        await queue.put(None)

    asyncio.create_task(_finalizer())

    while True:
        result = await queue.get()
        if result is None:
            break
        yield result
