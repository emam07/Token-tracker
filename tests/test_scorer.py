"""Unit tests for the efficiency scorer."""
from token_tracker.analyzer.scorer import compute_score, score_label
from token_tracker.core.models import Warning


def _w(severity: str) -> Warning:
    return Warning(rule="TEST", severity=severity, message="m", suggestion="s")


def test_score_starts_at_100_with_no_warnings():
    assert compute_score([], estimated_tokens=10) == 100


def test_high_warning_subtracts_20():
    assert compute_score([_w("high")], estimated_tokens=10) == 80


def test_medium_warning_subtracts_10():
    assert compute_score([_w("medium")], estimated_tokens=10) == 90


def test_low_warning_subtracts_5():
    assert compute_score([_w("low")], estimated_tokens=10) == 95


def test_multiple_warnings_compound():
    warnings = [_w("high"), _w("medium"), _w("low")]
    assert compute_score(warnings, estimated_tokens=10) == 100 - 20 - 10 - 5


def test_token_penalty_over_1000():
    assert compute_score([], estimated_tokens=1500) == 90


def test_token_penalty_over_3000():
    assert compute_score([], estimated_tokens=4000) == 80


def test_score_clamps_at_zero():
    warnings = [_w("high")] * 10
    assert compute_score(warnings, estimated_tokens=10) == 0


def test_score_label_efficient():
    assert score_label(95)[0] == "Efficient"
    assert score_label(80)[0] == "Efficient"


def test_score_label_acceptable():
    assert score_label(70)[0] == "Acceptable"


def test_score_label_wasteful():
    assert score_label(50)[0] == "Wasteful"


def test_score_label_very_wasteful():
    assert score_label(20)[0] == "Very wasteful"
