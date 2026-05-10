from token_tracker.core.models import Warning

_PENALTY = {"high": 20, "medium": 10, "low": 5}


def compute_score(warnings: list[Warning], estimated_tokens: int) -> int:
    penalty = sum(_PENALTY.get(w.severity, 0) for w in warnings)
    if estimated_tokens > 3000:
        penalty += 20
    elif estimated_tokens > 1000:
        penalty += 10
    return max(0, min(100, 100 - penalty))


def score_label(score: int) -> tuple[str, str]:
    if score >= 80:
        return "Efficient", "green"
    if score >= 60:
        return "Acceptable", "yellow"
    if score >= 40:
        return "Wasteful", "red"
    return "Very wasteful", "bold red"
