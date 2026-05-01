from datetime import datetime

from src.briefing.formatter import format_briefing


PROFILE = {
    "report": {
        "title_en": "AI Policy and the Startup Climate",
    }
}


def test_format_briefing_reports_when_no_recent_social_posts(monkeypatch):
    monkeypatch.setenv("LOOKBACK_HOURS", "25")

    result = format_briefing(
        articles=[],
        executive_summary="",
        profile=PROFILE,
        generated_at=datetime(2026, 5, 1, 12, 0),
        social_account_count=7,
    )

    assert "No recent social posts found" in result
    assert "7 followed accounts" in result
    assert "last 25 hours" in result


def test_format_briefing_reports_non_auth_social_failures():
    result = format_briefing(
        articles=[],
        executive_summary="",
        profile=PROFILE,
        generated_at=datetime(2026, 5, 1, 12, 0),
        social_fetch_failures=["@ylecun (HTTP 404)", "@sama (ReadTimeout)"],
        social_account_count=7,
    )

    assert "Some social feeds could not be fetched" in result
    assert "@ylecun (HTTP 404)" in result
    assert "This is not the same as 'no recent posts'" in result