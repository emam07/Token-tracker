from __future__ import annotations

from token_tracker.analyzer.rules import RULES, check_wall_of_text
from token_tracker.analyzer.scorer import compute_score
from token_tracker.core.models import PromptAnalysis, Warning
from token_tracker.core.tracker import _DEFAULT_COSTS, MODEL_COSTS

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _encoder = False   # mark as unavailable so we don't retry
    return _encoder if _encoder is not False else None


def estimate_tokens(text: str) -> int:
    enc = _get_encoder()
    if enc:
        return len(enc.encode(text))
    return max(1, len(text) // 4)  # fallback: 1 token ≈ 4 chars


def analyze(prompt: str, model: str = "claude-sonnet-4-6") -> PromptAnalysis:
    from token_tracker.optimizer.rewriter import optimize

    estimated_tokens = estimate_tokens(prompt)

    warnings: list[Warning] = []
    for rule_fn in RULES:
        result = rule_fn(prompt)
        if result:
            warnings.append(result)

    wall = check_wall_of_text(prompt, estimated_tokens)
    if wall:
        warnings.append(wall)

    score = compute_score(warnings, estimated_tokens)

    costs = MODEL_COSTS.get(model, _DEFAULT_COSTS)
    estimated_cost = estimated_tokens * costs["input"] / 1_000_000

    rewrite = optimize(prompt, warnings)
    rewrite_tokens = estimate_tokens(rewrite) if rewrite else estimated_tokens
    token_savings = estimated_tokens - rewrite_tokens

    return PromptAnalysis(
        estimated_input_tokens=estimated_tokens,
        estimated_cost_usd=estimated_cost,
        efficiency_score=score,
        warnings=warnings,
        suggested_rewrite=rewrite,
        token_savings=token_savings,
    )
