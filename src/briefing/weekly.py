"""
Weekly round-up — consolidates the past 7 daily briefings into one document.

Reads the N most recent files from briefings/, calls the LLM to de-duplicate
stories and synthesise a weekly view, then writes to roundups/.

Usage:
    python -m src.briefing.weekly

Environment variables:
    BRIEFINGS_DIR   Directory containing daily briefing .md files (default: briefings)
    ROUNDUPS_DIR    Output directory (default: roundups)
"""

import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from textwrap import dedent
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("briefing.weekly")

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
BRIEFINGS_DIR = Path(os.environ.get("BRIEFINGS_DIR", "briefings"))
ROUNDUPS_DIR = Path(os.environ.get("ROUNDUPS_DIR", "roundups"))


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _build_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def find_briefings_for_week() -> list[Path]:
    """
    Return one briefing per calendar day for the past 7 days, sorted oldest-first.

    Filename format: briefing_YYYY-MM-DD_HHMM.md
    When multiple runs exist for the same date (e.g. manual re-runs with a different model),
    only the latest run for that day is used — later timestamps replace earlier ones.
    """
    today = datetime.now(ZoneInfo("Europe/Amsterdam")).date()
    cutoff = today - timedelta(days=6)

    by_date: dict[date, list[Path]] = {}
    for f in BRIEFINGS_DIR.glob("briefing_*.md"):
        # stem: briefing_2026-04-27_0750  →  parts[1] = "2026-04-27"
        parts = f.stem.split("_")
        if len(parts) < 3:
            continue
        try:
            file_date = date.fromisoformat(parts[1])
        except ValueError:
            continue
        if file_date >= cutoff:
            by_date.setdefault(file_date, []).append(f)

    # For each date keep only the latest run (filename sort on HHMM suffix is sufficient)
    return [sorted(files)[-1] for _, files in sorted(by_date.items())]


def generate_weekly_roundup(briefing_texts: list[tuple[str, str]], profile: dict) -> str:
    """Generate a weekly round-up from (filename, content) pairs. Returns markdown."""
    model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
    client = _build_client()
    report = profile["report"]

    combined = "\n\n".join(
        f"=== BRIEFING: {name} ===\n{content}"
        for name, content in briefing_texts
    )

    system_msg = dedent(f"""\
        You are compiling a weekly news round-up for a senior policy analyst at {report['perspective']}.
        The analyst is writing a report on: "{report['title_en']}"
        Write in English. Use clear, analytical language suitable for a central bank analyst.
    """)

    user_msg = dedent(f"""\
        Below are {len(briefing_texts)} daily briefings from the past week.

        Create a weekly round-up with exactly this structure:

        # Weekly Round-Up — Week [ISO week number], [year]
        *Based on [N] daily briefings · [oldest date] to [newest date]*

        ## Summary of the Week
        3-5 sentences covering the most important developments of the week.
        Open with the most substantive finding. Do not start with "This week" or "In the past week".
        For each claim or development you mention, link to the specific article(s) that support it
        using inline markdown links, e.g. "The EU published new AI liability rules ([source](url))."

                ## What Were Followed Accounts Discussing This Week?
                Pull the "What Are Followed Accounts Discussing?" sections from each daily briefing
                and synthesise a weekly view: which themes recurred, what evolved across the week.
                For every concrete development, policy move, funding event, company update, or other
                factual claim you mention in this section, include inline markdown links to the relevant
                article URL(s) from the earlier daily briefings that support it.
                If no social sections were present in any briefing, omit this section entirely.

        ## Most Relevant Items
        List all Tier 1 and notable Tier 2 articles, de-duplicated:
        - Group items that cover the same event or topic into one entry
        - For each unique story: write a 2-3 sentence summary, note which briefing(s) surfaced it
          using short date labels like "Mon 27 Apr" or "Tue 28 Apr", and include the original URL(s)
          as markdown links
        - Sort by relevance: most important first

        ---
        *[N] unique items · [N] daily briefings*

        Briefings:
        {combined}
    """)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=4000,
    )
    return response.choices[0].message.content.strip()


def build_roundup_filename(now: datetime) -> str:
    """Return a timestamped weekly roundup filename, mirroring daily briefing uniqueness."""
    return f"roundup_{now:%Y-%m-%d_%H%M}.md"


def main() -> None:
    logger.info("Starting weekly round-up")

    profile = load_yaml(CONFIG_DIR / "report_profile.yaml")

    briefing_files = find_briefings_for_week()
    if not briefing_files:
        logger.error(f"No briefing files found in {BRIEFINGS_DIR} — exiting")
        sys.exit(1)

    logger.info(f"Processing {len(briefing_files)} briefings: {[f.name for f in briefing_files]}")

    briefing_texts = [(f.name, f.read_text(encoding="utf-8")) for f in briefing_files]

    weekly_md = generate_weekly_roundup(briefing_texts, profile)

    ROUNDUPS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(ZoneInfo("Europe/Amsterdam"))
    filename = build_roundup_filename(now)
    output_path = ROUNDUPS_DIR / filename

    output_path.write_text(weekly_md, encoding="utf-8")
    logger.info(f"Weekly round-up written to {output_path}")
    print(str(output_path))


if __name__ == "__main__":
    main()
