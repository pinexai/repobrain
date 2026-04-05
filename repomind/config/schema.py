from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitConfig(BaseModel):
    max_commits: int = Field(default=10_000, gt=0, description="Max git history depth — no hardcoded limits")
    decay_halflife_days: float = Field(default=180.0, gt=0, description="Exponential decay half-life for temporal scoring")
    cochange_window_days: int = Field(default=90, gt=0)
    branch: str = "main"
    cochange_min_score: float = Field(default=0.3, ge=0, le=1)


class LLMConfig(BaseModel):
    provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    model: str = "claude-sonnet-4-6"
    generation_concurrency: int = Field(default=5, gt=0, description="Parallel doc generation limit")
    embedding_model: str = "text-embedding-3-small"
    embedding_concurrency: int = Field(default=10, gt=0)
    max_tokens: int = Field(default=4096, gt=0)
    temperature: float = Field(default=0.2, ge=0, le=1)


class IndexingConfig(BaseModel):
    worker_processes: int = Field(
        default_factory=lambda: max(1, (os.cpu_count() or 4) * 2),
        gt=0,
    )
    chunk_size_chars: int = Field(default=512, gt=0)
    languages: list[str] = Field(default_factory=list, description="Empty = auto-detect all")
    exclude_patterns: list[str] = Field(
        default_factory=lambda: [
            "**/node_modules/**",
            "**/.venv/**",
            "**/venv/**",
            "**/dist/**",
            "**/build/**",
            "**/__pycache__/**",
            "**/.git/**",
            "**/*.min.js",
            "**/*.lock",
        ]
    )
    max_file_size_bytes: int = Field(default=500_000, gt=0)
    skip_binary: bool = True


class WebhookConfig(BaseModel):
    secret: str = ""
    port: int = Field(default=8765, gt=0)
    github_token: str = ""
    post_pr_comments: bool = True


class MCPConfig(BaseModel):
    port: int = Field(default=8766, gt=0)
    host: str = "127.0.0.1"


class RepomindConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REPOMIND_",
        env_nested_delimiter="__",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    repo_path: Path = Field(default_factory=Path.cwd)
    data_dir: Path = Field(default=Path(".repomind"))
    git: GitConfig = Field(default_factory=GitConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    indexing: IndexingConfig = Field(default_factory=IndexingConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    github_token: str = ""

    @model_validator(mode="after")
    def resolve_data_dir(self) -> "RepomindConfig":
        if not self.data_dir.is_absolute():
            self.data_dir = self.repo_path / self.data_dir
        return self

    @property
    def db_path(self) -> Path:
        return self.data_dir / "repomind.db"

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "vectors"

    @property
    def graph_path(self) -> Path:
        return self.data_dir / "graph.graphml"

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
