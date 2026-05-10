"""Integration test for TrackedClient using a mocked Anthropic SDK."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_usage():
    """Fake `usage` object as returned by the real Anthropic SDK."""
    u = MagicMock()
    u.input_tokens = 25
    u.output_tokens = 10
    u.cache_read_input_tokens = 0
    u.cache_creation_input_tokens = 0
    return u


@pytest.fixture
def mock_response(mock_usage):
    r = MagicMock()
    r.usage = mock_usage
    return r


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Redirect SQLite to a tmp path so tests don't touch the real DB."""
    import token_tracker.storage.db as db_module
    db_path = tmp_path / "usage.db"
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    yield db_path


def test_tracked_client_logs_usage_on_create(tmp_db, mock_response):
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response

        from token_tracker import TrackedClient

        client = TrackedClient(
            api_key="fake-key",
            session_name="test-session",
            analyze=False,            # skip pre-flight noise
            interactive=False,
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": "Hello"}],
        )

        assert response is mock_response

        # Verify the row landed in SQLite
        from token_tracker.storage.db import get_usage_today
        row = get_usage_today()
        assert row["requests"] == 1
        assert row["input_tokens"] == 25
        assert row["output_tokens"] == 10


def test_tracked_client_runs_preflight_when_enabled(tmp_db, mock_response):
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response

        from token_tracker import TrackedClient

        client = TrackedClient(
            api_key="fake-key",
            session_name="test-session",
            analyze=True,
            interactive=False,
            warn_threshold=0,   # never trigger a warning display
        )

        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": "tell me something about Python"}],
        )

        from token_tracker.storage.db import get_usage_today
        row = get_usage_today()
        assert row["requests"] == 1
        assert row["flagged_count"] == 1   # vague prompt should be flagged
