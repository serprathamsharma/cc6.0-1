"""Pytest configuration."""
import os
import pytest

# Force demo mode in tests
os.environ["DEMO_MODE"] = "true"
os.environ["REPLAY_MODE"] = "true"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["APP_SECRET_KEY"] = "test-secret-key-32-chars-exactly!"
