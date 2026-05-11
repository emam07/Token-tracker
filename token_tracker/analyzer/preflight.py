from __future__ import annotations

import warnings as _warnings

from token_tracker.analyzer.rules import RULES, check_wall_of_text
from token_tracker.analyzer.scorer import compute_score
from token_tracker.core.models import PromptAnalysis, Warning
from token_tracker.core.tracker import _DEFAULT_COSTS, MODEL_COSTS, _normalize_model

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _warnings.warn(
                "tiktoken not available — falling back to character-based token estimation "
                "(characters / 4). Token counts may be inaccurate. "
                "Fix: pip install tiktoken",
                stacklevel=3,
            )
            _encoder = False
    return _encoder if _encoder is not False else None


def estimate_tokens(text: str) -> int:
    enc = _get_encoder()
    if enc:
        return len(enc.encode(text))
    return max(1, len(text) // 4)


def analyze(prompt: str, model: str = "claude-sonnet-4-6") -> PromptAnalysis:
    from token_tracker.optimizer.rewriter import optimize

    estimated_tokens = estimate_tokens(prompt)

    rule_warnings: list[Warning] = []
    for rule_fn in RULES:
        result = rule_fn(prompt)
        if result:
            rule_warnings.append(result)

    wall = check_wall_of_text(prompt, estimated_tokens)
    if wall:
        rule_warnings.append(wall)

    score = compute_score(rule_warnings, estimated_tokens)

    costs = MODEL_COSTS.get(_normalize_model(model), _DEFAULT_COSTS)
    estimated_cost = estimated_tokens * costs["input"] / 1_000_000

    if rule_warnings:
        rewrite = optimize(prompt, rule_warnings)
        rewrite_tokens = estimate_tokens(rewrite) if rewrite else estimated_tokens
        delta = estimated_tokens - rewrite_tokens
    else:
        rewrite = ""
        delta = 0

    return PromptAnalysis(
        estimated_input_tokens=estimated_tokens,
        estimated_cost_usd=estimated_cost,
        efficiency_score=score,
        warnings=rule_warnings,
        suggested_rewrite=rewrite,
        token_delta=delta,
    )
