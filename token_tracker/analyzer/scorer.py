from token_tracker.core.models import Warning

_PENALTY = {"high": 20, "medium": 10, "low": 5}


def compute_score(warnings: list[Warning], estimated_tokens: int) -> int:
    penalty = sum(_PENALTY.get(w.severity, 0) for w in warnings)
    if estimated_tokens > 50_000:
        penalty += 50
    elif estimated_tokens > 10_000:
        penalty += 35
    elif estimated_tokens > 3_000:
        penalty += 20
    elif estimated_tokens > 1_000:
        penalty += 10
    elif estimated_tokens > 500:
        penalty += 5
    return max(0, min(100, 100 - penalty))


def score_label(score: int) -> tuple[str, str]:
    if score >= 80:
        return "Efficient", "green"
    if score >= 60:
        return "Acceptable", "yellow"
    if score >= 40:
        return "Wasteful", "red"
    return "Very wasteful", "bold red"
