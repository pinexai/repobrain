"""
TokenspyCostAdapter — wraps every Anthropic call with cost tracking.
Integrates with the user's own tokenspy library (pinexai/tokenspy).
Every LLM call in repomind records cost to the llm_costs SQL table.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from ..storage.sql import AsyncSQLiteDB
from ..storage.sql.repositories.costs import CostRepository
from ..utils.logging import get_logger

log = get_logger(__name__)

# Pricing per 1M tokens (update as needed)
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}


@dataclass
class CostRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    operation: str
    file_path: str | None = None


class TokenspyCostTracker:
    def __init__(self, db: AsyncSQLiteDB, repo_id: str) -> None:
        self._repo = CostRepository(db)
        self._repo_id = repo_id
        self._session_cost: float = 0.0
        self._session_tokens: int = 0

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        pricing = _PRICING.get(model, {"input": 3.0, "output": 15.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

    async def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
        file_path: str | None = None,
    ) -> float:
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        self._session_cost += cost
        self._session_tokens += input_tokens + output_tokens
        try:
            await self._repo.record(
                repo_id=self._repo_id,
                operation=operation,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                file_path=file_path,
            )
        except Exception as e:
            log.warning("cost_record_failed", error=str(e))
        return cost

    @property
    def session_cost(self) -> float:
        return self._session_cost

    @property
    def session_tokens(self) -> int:
        return self._session_tokens

    async def get_summary(self) -> dict:
        return await self._repo.get_summary(self._repo_id)

    async def get_by_operation(self) -> list[dict]:
        return await self._repo.get_by_operation(self._repo_id)
