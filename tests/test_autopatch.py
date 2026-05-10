"""Tests for the transparent autopatch — monkey-patching anthropic.Anthropic."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    import token_tracker.storage.db as db_module
    db_path = tmp_path / "usage.db"
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    yield db_path


@pytest.fixture(autouse=True)
def reset_patch():
    """Ensure autopatch state is clean before and after each test."""
    from token_tracker import autopatch
    autopatch.unpatch()
    yield
    autopatch.unpatch()


def _make_mock_anthropic(input_tokens=10, output_tokens=5):
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_input_tokens = 0
    usage.cache_creation_input_tokens = 0

    response = MagicMock()
    response.usage = usage

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_patch_replaces_anthropic_anthropic(tmp_db, monkeypatch):
    import anthropic

    from token_tracker.autopatch import patch

    original = anthropic.Anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: _make_mock_anthropic())

    patch()

    assert anthropic.Anthropic is not original


def test_patched_anthropic_returns_tracked_client(tmp_db, monkeypatch):
    import anthropic

    from token_tracker.autopatch import patch
    from token_tracker.core.client import TrackedClient

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: _make_mock_anthropic())

    patch()
    client = anthropic.Anthropic()

    assert isinstance(client, TrackedClient)


def test_patch_is_idempotent(tmp_db, monkeypatch):
    import anthropic

    from token_tracker.autopatch import patch

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: _make_mock_anthropic())

    patch()
    first = anthropic.Anthropic
    patch()  # second call should be a no-op
    assert anthropic.Anthropic is first


def test_unpatch_restores_original(tmp_db, monkeypatch):
    import anthropic

    from token_tracker.autopatch import patch, unpatch

    original = MagicMock()
    monkeypatch.setattr(anthropic, "Anthropic", original)

    patch()
    unpatch()

    assert anthropic.Anthropic is original


def test_patched_client_logs_usage(tmp_db, monkeypatch):
    import anthropic

    from token_tracker.autopatch import patch

    mock_inner = _make_mock_anthropic(input_tokens=20, output_tokens=8)
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: mock_inner)

    patch(analyze=False)
    client = anthropic.Anthropic()

    client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=64,
        messages=[{"role": "user", "content": "Hello"}],
    )

    from token_tracker.storage.db import get_usage_today
    row = get_usage_today()
    assert row["requests"] == 1
    assert row["input_tokens"] == 20
    assert row["output_tokens"] == 8
