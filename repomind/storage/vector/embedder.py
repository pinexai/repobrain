from __future__ import annotations

import asyncio
import os
from typing import Any

from ...utils.logging import get_logger

log = get_logger(__name__)

# Prevent tokenizer parallelism deadlocks with ProcessPoolExecutor
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Dimension constants
OPENAI_DIM = 1536
LOCAL_DIM = 384


class LocalEmbedder:
    """
    Embedding using sentence-transformers — no API key required.

    Uses a single sequential semaphore to avoid conflicts between
    loky (sentence-transformers) and the parse ProcessPoolExecutor.
    """

    _model: Any = None  # shared singleton across instances
    _load_lock: asyncio.Lock | None = None

    def __init__(self, concurrency: int = 4) -> None:
        # Force sequential — prevents loky/multiprocessing conflicts on Python 3.14
        self._sem = asyncio.Semaphore(1)
        self.dim = LOCAL_DIM

    def _load_sync(self) -> None:
        if LocalEmbedder._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            LocalEmbedder._model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                # Disable multi-process tokenization entirely
                tokenizer_kwargs={"use_fast": True},
            )

    async def embed(self, text: str) -> list[float]:
        async with self._sem:
            try:
                loop = asyncio.get_running_loop()
                # Load model synchronously in executor (one-time cost)
                if LocalEmbedder._model is None:
                    await loop.run_in_executor(None, self._load_sync)
                # Encode — run in thread to not block event loop
                vec = await loop.run_in_executor(
                    None,
                    lambda: LocalEmbedder._model.encode(
                        text[:4096],
                        batch_size=1,
                        show_progress_bar=False,
                    ).tolist()
                )
                return vec
            except Exception as e:
                log.warning("local_embedding_failed", error=str(e))
                return [0.0] * LOCAL_DIM

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Sequential — intentional to avoid multiprocessing conflicts
        results = []
        for t in texts:
            results.append(await self.embed(t))
        return results

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 512) -> list[str]:
        chunks: list[str] = []
        overlap = chunk_size // 4
        start = 0
        while start < len(text):
            chunks.append(text[start:start + chunk_size])
            start += chunk_size - overlap
        return chunks


class AsyncEmbedder:
    """Async wrapper around OpenAI-compatible embedding API."""

    def __init__(self, model: str, client: Any, concurrency: int = 10) -> None:
        self._model = model
        self._client = client
        self._sem = asyncio.Semaphore(concurrency)
        self.dim = OPENAI_DIM

    async def embed(self, text: str) -> list[float]:
        async with self._sem:
            try:
                resp = await self._client.embeddings.create(
                    model=self._model,
                    input=text[:8192],
                )
                return resp.data[0].embedding
            except Exception as e:
                log.warning("embedding_failed", error=str(e))
                return [0.0] * OPENAI_DIM

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.gather(*[self.embed(t) for t in texts])

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 512) -> list[str]:
        """Split text into overlapping chunks for better retrieval."""
        chunks: list[str] = []
        overlap = chunk_size // 4
        start = 0
        while start < len(text):
            chunks.append(text[start:start + chunk_size])
            start += chunk_size - overlap
        return chunks
