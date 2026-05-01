"""
Tests for src/briefing/processor.py.

All tests mock the OpenAI client so no real API calls are made.
"""

import json
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.briefing.models import Article
from src.briefing.processor import generate_executive_summary, score_articles

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROFILE = {
    "report": {
        "title_en": "AI Policy and the Startup Climate",
        "perspective": "central bank analyst",
    },
    "core_focus": "AI regulation, startup investment",
    "themes": ["AI", "regulation"],
    "key_actors": ["European Commission", "OECD"],
    "relevance_tiers": {
        "tier_0": {"label": "Irrelevant", "description": "No connection to report topic."},
        "tier_1": {"label": "Core", "description": "Directly addresses the report topic."},
        "tier_2": {"label": "Background", "description": "Loosely related context."},
        "tier_3": {"label": "Peripheral", "description": "Credible source, weak connection."},
    },
}


def _article(title="Test Article", tier=0):
    return Article(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        source_name="Test Source",
        category="tech",
        language="en",
        published=datetime(2026, 4, 24, 9, 0),
        summary="A short summary.",
        tier=tier,
    )


def _mock_response(payload: list[dict]) -> MagicMock:
    """Return a mocked OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# score_articles — model ID
# ---------------------------------------------------------------------------


def test_score_articles_uses_correct_default_model():
    """Default model must be anthropic/claude-sonnet-4.6 (period, not hyphen)."""
    articles = [_article()]
    captured = {}

    def fake_create(**kwargs):
        captured["model"] = kwargs.get("model")
        return _mock_response([{"index": 0, "tier": 1, "reason": "relevant"}])

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = fake_create

    with patch("src.briefing.processor._build_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
            os.environ.pop("OPENROUTER_MODEL", None)
            score_articles(articles, PROFILE)

    assert captured["model"] == "anthropic/claude-sonnet-4.6", (
        f"Wrong model ID: {captured['model']!r} — OpenRouter requires a period before the minor version"
    )


def test_score_articles_respects_env_model_override():
    articles = [_article()]
    captured = {}

    def fake_create(**kwargs):
        captured["model"] = kwargs.get("model")
        return _mock_response([{"index": 0, "tier": 2, "reason": "ok"}])

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = fake_create

    with patch("src.briefing.processor._build_client", return_value=mock_client):
        with patch.dict(os.environ, {"OPENROUTER_MODEL": "anthropic/claude-haiku-4.5"}, clear=False):
            score_articles(articles, PROFILE)

    assert captured["model"] == "anthropic/claude-haiku-4.5"


# ---------------------------------------------------------------------------
# score_articles — success path
# ---------------------------------------------------------------------------


def test_score_articles_assigns_tiers():
    articles = [_article("Article A"), _article("Article B")]
    payload = [
        {"index": 0, "tier": 1, "reason": "core topic"},
        {"index": 1, "tier": 3, "reason": "peripheral"},
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(payload)

    with patch("src.briefing.processor._build_client", return_value=mock_client):
        result, ok = score_articles(articles, PROFILE)

    assert ok is True
    assert result[0].tier == 1
    assert result[0].tier_reason == "core topic"
    assert result[1].tier == 3


def test_score_articles_handles_dict_wrapped_response():
    """Model sometimes wraps the array in a dict; parser must unwrap it."""
    articles = [_article()]
    wrapped = {"articles": [{"index": 0, "tier": 2, "reason": "background"}]}
    msg = MagicMock()
    msg.content = json.dumps(wrapped)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = resp

    with patch("src.briefing.processor._build_client", return_value=mock_client):
        result, ok = score_articles(articles, PROFILE)

    assert ok is True
    assert result[0].tier == 2


def test_score_articles_empty_list():
    result, ok = score_articles([], PROFILE)
    assert result == []
    assert ok is True


# ---------------------------------------------------------------------------
# score_articles — failure paths
# ---------------------------------------------------------------------------


def test_score_articles_returns_false_on_bad_request_error():
    """A BadRequestError (HTTP 400 from OpenRouter on unknown model ID) must be caught."""
    from openai import BadRequestError

    articles = [_article(), _article("B")]
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_client.chat.completions.create.side_effect = BadRequestError(
        message="No endpoints found matching your data policy",
        response=mock_response,
        body={"error": {"message": "No endpoints found", "code": 400}},
    )

    with patch("src.briefing.processor._build_client", return_value=mock_client):
        result, ok = score_articles(articles, PROFILE)

    assert ok is False
    assert all(a.tier == 3 for a in result)
    assert all("BadRequestError" in a.tier_reason for a in result)


def test_score_articles_returns_false_on_missing_api_key():
    """EnvironmentError from _build_client (no API key) must be caught gracefully."""
    articles = [_article()]

    with patch(
        "src.briefing.processor._build_client",
        side_effect=EnvironmentError("OPENROUTER_API_KEY is not set"),
    ):
        result, ok = score_articles(articles, PROFILE)

    assert ok is False
    assert result[0].tier == 3
    assert "API key not set" in result[0].tier_reason


def test_score_articles_does_not_overwrite_already_scored():
    """Articles that already have a tier set should not be reset to 3 on failure."""
    articles = [_article(tier=2)]

    with patch(
        "src.briefing.processor._build_client",
        side_effect=EnvironmentError("no key"),
    ):
        result, ok = score_articles(articles, PROFILE)

    assert ok is False
    assert result[0].tier == 2  # was already scored, not overwritten


# ---------------------------------------------------------------------------
# generate_executive_summary
# ---------------------------------------------------------------------------


def test_generate_executive_summary_uses_correct_default_model():
    captured = {}

    def fake_create(**kwargs):
        captured["model"] = kwargs.get("model")
        msg = MagicMock()
        msg.content = "Executive summary text."
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        return resp

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = fake_create

    articles = [_article(tier=1)]
    with patch("src.briefing.processor._build_client", return_value=mock_client):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_MODEL", None)
            generate_executive_summary(articles, PROFILE)

    assert captured["model"] == "anthropic/claude-sonnet-4.6"


def test_generate_executive_summary_skips_when_no_tier1():
    result = generate_executive_summary([_article(tier=2), _article(tier=3)], PROFILE)
    assert result == ""


def test_generate_executive_summary_returns_empty_on_error():
    articles = [_article(tier=1)]
    with patch(
        "src.briefing.processor._build_client",
        side_effect=Exception("network error"),
    ):
        result = generate_executive_summary(articles, PROFILE)
    assert result == ""
