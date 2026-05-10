"""Unit tests for the prompt rewriter."""
from token_tracker.core.models import Warning
from token_tracker.optimizer.rewriter import optimize


def _w(rule: str, severity: str = "low") -> Warning:
    return Warning(rule=rule, severity=severity, message="m", suggestion="s")


def test_optimize_returns_empty_string_when_no_warnings():
    assert optimize("any prompt", warnings=[]) == ""


def test_optimize_strips_filler_phrases():
    prompt = "Please could you kindly write the function"
    result = optimize(prompt, warnings=[_w("FILLER_WORDS")])
    assert "please" not in result.lower()
    assert "could you kindly" not in result.lower()
    assert "write the function" in result.lower()


def test_optimize_replaces_vague_intent():
    prompt = "tell me something about Python"
    result = optimize(prompt, warnings=[_w("VAGUE_INTENT", "high")])
    assert "tell me something about" not in result.lower()
    assert result.lower().startswith("explain")


def test_optimize_replaces_open_ended_task():
    prompt = "explain everything about ML"
    result = optimize(prompt, warnings=[_w("OPEN_ENDED_TASK", "high")])
    assert "everything" not in result.lower()


def test_optimize_adds_format_constraint_when_missing():
    prompt = "List the Python frameworks"
    result = optimize(prompt, warnings=[_w("MISSING_FORMAT", "medium")])
    assert "numbered list" in result.lower()


def test_optimize_adds_scope_constraint_when_missing():
    prompt = "explain the GIL"
    result = optimize(prompt, warnings=[_w("MISSING_SCOPE", "medium")])
    assert "200 words" in result or "under" in result.lower()


def test_optimize_removes_duplicate_sentences():
    prompt = "Alice is the user. Alice is the user. Now answer."
    result = optimize(prompt, warnings=[_w("REDUNDANT_CONTEXT", "medium")])
    # only one occurrence of "Alice is the user" should remain
    assert result.lower().count("alice is the user") == 1


def test_optimize_capitalizes_first_letter():
    prompt = "please write the function"
    result = optimize(prompt, warnings=[_w("FILLER_WORDS")])
    assert result[0].isupper()


def test_optimize_removes_dangling_conjunctions():
    prompt = "please write the function and please add docs"
    result = optimize(prompt, warnings=[_w("FILLER_WORDS")])
    assert not result.rstrip(".!?").rstrip().lower().endswith(("and", "or", "but"))
