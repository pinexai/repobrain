from __future__ import annotations

import asyncio
from typing import Any

from ...utils.logging import get_logger

log = get_logger(__name__)


class AsyncEmbedder:
    """Async wrapper around OpenAI-compatible embedding API."""

    def __init__(self, model: str, client: Any, concurrency: int = 10) -> None:
        self._model = model
        self._client = client
        self._sem = asyncio.Semaphore(concurrency)

    async def embed(self, text: str) -> list[float]:
        async with self._sem:
            try:
                resp = await self._client.embeddings.create(
                    model=self._model,
                    input=text[:8192],  # token limit guard
                )
                return resp.data[0].embedding
            except Exception as e:
                log.warning("embedding_failed", error=str(e))
                return [0.0] * 1536  # zero vector as fallback

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        tasks = [self.embed(t) for t in texts]
        return await asyncio.gather(*tasks)

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 512) -> list[str]:
        """Split text into overlapping chunks for better retrieval."""
        chunks: list[str] = []
        overlap = chunk_size // 4
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks
