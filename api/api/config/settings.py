"""Application settings loaded from environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_secret_key: str = "changeme-32-char-secret-key-here"
    demo_mode: bool = False
    replay_mode: bool = False

    # DB
    database_url: str = "postgresql+asyncpg://scoutiq:scoutiq_dev_pass@localhost:5432/scoutiq"
    database_url_sync: str = "postgresql://scoutiq:scoutiq_dev_pass@localhost:5432/scoutiq"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI
    openai_api_key: str = ""
    model_planner: str = "gpt-4o"
    model_extract: str = "gpt-4o"
    model_fast: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-large"
    embedding_dims: int = 1536
    llm_pricing_file: str = ""

    # Search
    tavily_api_key: str = ""
    brave_api_key: str = ""

    # Snapshots
    snapshot_backend: str = "local"
    snapshot_local_dir: str = "/data/snapshots"
    snapshot_s3_bucket: str = ""
    snapshot_s3_endpoint: str = ""
    snapshot_s3_access_key: str = ""
    snapshot_s3_secret_key: str = ""

    # Rate limits
    rate_limit_default_rps: float = 1.0

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    @property
    def is_demo(self) -> bool:
        """True when demo mode is forced or API keys are absent."""
        if self.demo_mode or self.replay_mode:
            return True
        if not self.openai_api_key:
            return True
        return False

    @property
    def pricing(self) -> dict[str, Any]:
        path = self.llm_pricing_file or str(
            Path(__file__).parent / "pricing.json"
        )
        with open(path) as f:
            return json.load(f)


settings = Settings()
