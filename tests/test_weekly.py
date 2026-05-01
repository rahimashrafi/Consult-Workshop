from datetime import datetime
from unittest.mock import MagicMock, patch

from src.briefing.weekly import build_roundup_filename, generate_weekly_roundup


def test_build_roundup_filename_uses_date_and_time():
    now = datetime(2026, 4, 27, 20, 30)

    assert build_roundup_filename(now) == "roundup_2026-04-27_2030.md"


def test_generate_weekly_roundup_requires_links_in_social_section():
    captured = {}

    def fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        message = MagicMock()
        message.content = "# Weekly Round-Up"
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = fake_create

    profile = {
        "report": {
            "title_en": "AI Policy and the Startup Climate",
            "perspective": "central bank analyst",
        }
    }

    with patch("src.briefing.weekly._build_client", return_value=mock_client):
        generate_weekly_roundup([
            ("briefing_2026-04-27_0750.md", "## What Are Followed Accounts Discussing?\nA startup funding round."),
        ], profile)

    user_prompt = captured["messages"][1]["content"]
    assert "What Were Followed Accounts Discussing This Week?" in user_prompt
    assert "inline markdown links" in user_prompt
    assert "earlier daily briefings" in user_prompt
    assert user_prompt.index("## Summary of the Week") < user_prompt.index("## What Were Followed Accounts Discussing This Week?")
    assert user_prompt.index("## What Were Followed Accounts Discussing This Week?") < user_prompt.index("## Most Relevant Items")