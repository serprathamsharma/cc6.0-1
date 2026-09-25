"""LLM client: OpenAI Responses API with retry, cost tracking, and model fallback."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

import openai
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from api.config.settings import settings

_client: Optional[openai.AsyncOpenAI] = None
_available_models: list[str] = []


def get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.openai_api_key or "demo")
    return _client


async def probe_models() -> list[str]:
    """Probe available models at startup."""
    global _available_models
    if not settings.openai_api_key:
        logger.warning("No OPENAI_API_KEY — running in DEMO MODE")
        _available_models = []
        return []
    try:
        client = get_client()
        models = await client.models.list()
        ids = [m.id for m in models.data]
        _available_models = ids
        logger.info(f"Probed {len(ids)} models")
        # Check and remap model IDs
        _remap_models(ids)
        return ids
    except Exception as e:
        logger.warning(f"Could not probe models: {e}")
        return []


def _remap_models(available: list[str]) -> None:
    """Remap placeholder model IDs to available ones."""
    candidates_planner = ["gpt-6-astra", "gpt-4o", "gpt-4o-2024-08-06"]
    candidates_extract = ["gpt-6-sol", "gpt-4o", "gpt-4o-2024-08-06"]
    candidates_fast = ["gpt-6-luna", "gpt-4o-mini", "gpt-4o-mini-2024-07-18"]

    for c in candidates_planner:
        if c in available:
            settings.model_planner = c
            break
    else:
        settings.model_planner = "gpt-4o"
        logger.warning("Planner model fallback -> gpt-4o")

    for c in candidates_extract:
        if c in available:
            settings.model_extract = c
            break
    else:
        settings.model_extract = "gpt-4o"

    for c in candidates_fast:
        if c in available:
            settings.model_fast = c
            break
    else:
        settings.model_fast = "gpt-4o-mini"


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = settings.pricing
    p = pricing.get(model, {"input_per_1m": 5.0, "output_per_1m": 15.0})
    return (input_tokens * p["input_per_1m"] + output_tokens * p["output_per_1m"]) / 1_000_000


async def llm_call(
    model: str,
    messages: list[dict],
    response_format: dict | None = None,
    purpose: str = "general",
    run_id: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Call the OpenAI chat completions API with retry and cost tracking."""
    if settings.is_demo:
        return json.dumps({"error": "demo_mode"})

    client = get_client()
    t0 = time.time()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or ""
            usage = resp.usage
            cost = _cost(model, usage.prompt_tokens, usage.completion_tokens)
            latency = int((time.time() - t0) * 1000)
            logger.info(f"LLM {model}/{purpose} in={usage.prompt_tokens} out={usage.completion_tokens} cost=${cost:.4f}")
            # TODO: persist to llm_calls table
            return content
        except openai.RateLimitError:
            await asyncio.sleep(2 ** attempt * 2)
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)

    return ""


async def moderate(text: str) -> bool:
    """Return True if content is safe. False if flagged."""
    if settings.is_demo:
        return True
    try:
        client = get_client()
        resp = await client.moderations.create(input=text)
        return not resp.results[0].flagged
    except Exception:
        return True  # fail open
