"""Unit tests for each pre-flight rule. Each rule has a positive + negative case."""
from token_tracker.analyzer.rules import (
    check_ambiguous_pronoun,
    check_filler_words,
    check_missing_format,
    check_missing_scope,
    check_open_ended_task,
    check_redundant_context,
    check_vague_intent,
    check_wall_of_text,
)


# VAGUE_INTENT
def test_vague_intent_triggers_on_tell_me_something():
    w = check_vague_intent("tell me something about Python")
    assert w is not None
    assert w.rule == "VAGUE_INTENT"
    assert w.severity == "high"


def test_vague_intent_skips_specific_request():
    assert check_vague_intent("List 3 Python web frameworks.") is None


# MISSING_FORMAT
def test_missing_format_triggers_on_unstructured_list_request():
    w = check_missing_format("give me the popular Python frameworks")
    assert w is not None
    assert w.rule == "MISSING_FORMAT"


def test_missing_format_skips_when_format_specified():
    assert check_missing_format("list 3 frameworks as a numbered list") is None


# MISSING_SCOPE
def test_missing_scope_triggers_on_open_explanation():
    w = check_missing_scope("explain how transformers work")
    assert w is not None
    assert w.rule == "MISSING_SCOPE"


def test_missing_scope_skips_when_scope_given():
    assert check_missing_scope("explain transformers in 3 sentences") is None


# FILLER_WORDS
def test_filler_words_triggers_on_courtesy_phrases():
    w = check_filler_words("Please could you kindly write the function")
    assert w is not None
    assert w.rule == "FILLER_WORDS"
    assert w.severity == "low"


def test_filler_words_skips_clean_prompt():
    assert check_filler_words("Write the function with a docstring.") is None


# REDUNDANT_CONTEXT
def test_redundant_context_triggers_on_duplicate_sentence():
    prompt = "The user is named Alice. The user is named Alice. Now answer."
    w = check_redundant_context(prompt)
    assert w is not None
    assert w.rule == "REDUNDANT_CONTEXT"


def test_redundant_context_skips_unique_content():
    assert check_redundant_context("Alice is the user. Bob is the admin.") is None


# WALL_OF_TEXT
def test_wall_of_text_triggers_on_long_unstructured_prompt():
    w = check_wall_of_text("a" * 10000, estimated_tokens=1500)
    assert w is not None
    assert w.rule == "WALL_OF_TEXT"


def test_wall_of_text_skips_structured_long_prompt():
    structured = "## Heading\n- item 1\n- item 2\n" + ("more text " * 200)
    assert check_wall_of_text(structured, estimated_tokens=1500) is None


def test_wall_of_text_skips_short_prompt():
    assert check_wall_of_text("short prompt", estimated_tokens=50) is None


# AMBIGUOUS_PRONOUN
def test_ambiguous_pronoun_triggers_on_short_fix_it():
    w = check_ambiguous_pronoun("fix it please")
    assert w is not None
    assert w.rule == "AMBIGUOUS_PRONOUN"


def test_ambiguous_pronoun_skips_long_prompt():
    long_prompt = " ".join(["word"] * 30) + " fix it"
    assert check_ambiguous_pronoun(long_prompt) is None


# OPEN_ENDED_TASK
def test_open_ended_task_triggers_on_explain_everything():
    w = check_open_ended_task("explain everything about machine learning")
    assert w is not None
    assert w.rule == "OPEN_ENDED_TASK"
    assert w.severity == "high"


def test_open_ended_task_skips_bounded_task():
    assert check_open_ended_task("summarize ML in 3 sentences") is None
