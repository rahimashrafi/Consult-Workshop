"""
Formats the scored articles into a clean Markdown briefing document.

Tier 0 items are excluded entirely.
Tier 3 items are hidden by default; set INCLUDE_TIER3=true to show them.
"""

import os
from datetime import datetime, timezone, timedelta

from .models import Article

CET = timezone(timedelta(hours=1))
TIER_LABELS = {
    1: "Perfectly relevant",
    2: "Relevant",
    3: "Low signal",
}


def format_briefing(
    articles: list[Article],
    executive_summary: str,
    profile: dict,
    generated_at: datetime | None = None,
    serendipity_names: list[str] | None = None,
    iterations_used: int = 1,
    scoring_ok: bool = True,
    social_auth_failures: list[str] | None = None,
    social_summary: str | None = None,
) -> str:
    if generated_at is None:
        generated_at = datetime.now(CET)

    include_tier3 = os.environ.get("INCLUDE_TIER3", "").lower() in ("true", "1", "yes")

    date_str = generated_at.strftime("%-d %B %Y")
    time_str = generated_at.strftime("%H:%M CET")
    report_title = profile["report"]["title_en"]

    lines: list[str] = []

    # Header
    lines += [
        f"# Daily Briefing — {date_str}",
        f"*Generated at {time_str} | Report: {report_title}*",
        "",
    ]

    # Warnings
    if not scoring_ok:
        lines += [
            "> ⚠️ **LLM scoring failed** — articles were not scored for relevance. "
            "Check that `OPENROUTER_API_KEY` is set correctly as a GitHub secret "
            "and that the model is available via OpenRouter.",
            "",
        ]
    if social_auth_failures:
        handles_str = ", ".join(f"@{h}" for h in social_auth_failures)
        lines += [
            f"> ⚠️ **Social media feeds failed to load** ({handles_str}) — "
            "the RSSHub access token needs to be renewed.",
            "",
        ]

    # Executive summary
    if executive_summary:
        lines += [
            "## Summary",
            "",
            executive_summary,
            "",
        ]

    # Social section
    if social_summary:
        lines += [
            "## What Are Followed Accounts Discussing?",
            "",
            social_summary,
            "",
        ]

    # Tiers — Tier 0 excluded, Tier 3 conditional
    tiers_to_show = (1, 2, 3) if include_tier3 else (1, 2)
    for tier in tiers_to_show:
        tier_articles = [a for a in articles if a.tier == tier]
        if not tier_articles:
            continue

        label = TIER_LABELS[tier]
        lines += [
            f"## {label} ({len(tier_articles)})",
            "",
        ]

        for a in sorted(tier_articles, key=lambda x: x.published, reverse=True):
            pub_str = a.published.astimezone(CET).strftime("%-d %b, %H:%M")
            lines.append(f"### [{a.title}]({a.url})")
            lines.append(f"*{a.source_name} · {pub_str}*")
            if a.summary:
                lines.append(f"\n{a.summary}")
            if a.tier_reason:
                lines.append(f"\n> {a.tier_reason}")
            lines.append("")

    # Footer
    excluded = [a for a in articles if a.tier == 0]
    tier3 = [a for a in articles if a.tier == 3]
    shown = [a for a in articles if a.tier in tiers_to_show]

    footer_parts = [f"{len(shown)} items · {_count_sources(shown)} sources"]
    if excluded:
        footer_parts.append(f"{len(excluded)} excluded (Tier 0 · not relevant)")
    if tier3 and not include_tier3:
        footer_parts.append(f"{len(tier3)} low signal hidden (set INCLUDE_TIER3=true to show)")
    if serendipity_names:
        footer_parts.append(f"Serendipity sources today: {', '.join(serendipity_names)}")
    if iterations_used > 1:
        footer_parts.append(f"Quality check: {iterations_used} iterations")

    lines += [
        "---",
        f"*{' · '.join(footer_parts)}*",
    ]

    return "\n".join(lines)


def _count_sources(articles: list[Article]) -> int:
    return len({a.source_name for a in articles})
