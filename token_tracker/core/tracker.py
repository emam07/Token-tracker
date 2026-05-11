import hashlib
import re

from token_tracker.core.models import UsageRecord
from token_tracker.storage.db import insert_usage_record

# Cost per 1M tokens (USD) — update when Anthropic changes pricing
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-7":   {"input": 15.00, "output": 75.00, "cache_read": 1.50,  "cache_write": 18.75},
    "claude-sonnet-4-6": {"input":  3.00, "output": 15.00, "cache_read": 0.30,  "cache_write":  3.75},
    "claude-haiku-4-5":  {"input":  0.80, "output":  4.00, "cache_read": 0.08,  "cache_write":  1.00},
}
_DEFAULT_COSTS = MODEL_COSTS["claude-sonnet-4-6"]


def _normalize_model(model: str) -> str:
    """Strip trailing date suffix from model IDs (e.g. claude-haiku-4-5-20251001 → claude-haiku-4-5)."""
    return re.sub(r"-\d{8}$", "", model or "")


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    c = MODEL_COSTS.get(_normalize_model(model), _DEFAULT_COSTS)
    return (
        input_tokens       * c["input"]        / 1_000_000
        + output_tokens    * c["output"]       / 1_000_000
        + cache_read_tokens  * c["cache_read"]   / 1_000_000
        + cache_write_tokens * c["cache_write"]  / 1_000_000
    )


def hash_prompt(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def log_usage(
    session_id: str,
    model: str,
    prompt: str,
    usage,
    efficiency_score: int | None = None,
    flagged: bool = False,
) -> UsageRecord:
    input_tokens  = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_read    = getattr(usage, "cache_read_input_tokens",      0) or 0
    cache_write   = getattr(usage, "cache_creation_input_tokens",  0) or 0

    record = UsageRecord(
        session_id=session_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        cost_usd=calculate_cost(model, input_tokens, output_tokens, cache_read, cache_write),
        prompt_hash=hash_prompt(prompt),
        efficiency_score=efficiency_score,
        flagged=flagged,
    )
    insert_usage_record(record)
    return record
