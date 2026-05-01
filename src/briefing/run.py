"""
Daily briefing — main entry point.

Usage:
    python -m src.briefing.run              # normal run
    python -m src.briefing.run --dry-run    # fetch and format, skip LLM scoring

Environment variables:
    SERENDIPITY_N       Number of serendipity sources to sample per run (default: 3)
    MAX_ITERATIONS      Max quality-pass iterations if Tier 1 count is low (default: 3)
    TIER1_THRESHOLD     Minimum Tier 1 articles to consider quality sufficient (default: 3)
    INCLUDE_TIER3       Set to 'true' to include Tier 3 (low signal) in output (default: false)
    LOOKBACK_HOURS      How many hours back to fetch articles (default: 25)
"""

import argparse
import logging
import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .fetchers.rss import fetch_rss_articles
from .fetchers.social import fetch_social_articles
from .formatter import format_briefing
from .processor import generate_executive_summary, generate_social_summary, score_articles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("briefing.run")

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "outputs"))


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main(dry_run: bool = False) -> None:
    logger.info("Starting daily briefing run")

    sources = load_yaml(CONFIG_DIR / "sources.yaml")
    profile = load_yaml(CONFIG_DIR / "report_profile.yaml")

    # --- Fetch core news sources ---
    news_articles: list = []
    news_articles += fetch_rss_articles(sources.get("rss_feeds", []))

    # Social media fetched separately — not mixed into the news scoring pipeline
    raw_social, social_auth_failures = fetch_social_articles(sources.get("social", {}))

    # Handle web_sources: items tagged type=rss are passed through the RSS fetcher
    web_as_rss = [
        s for s in sources.get("web_sources", []) if s.get("type") == "rss"
    ]
    if web_as_rss:
        news_articles += fetch_rss_articles(web_as_rss)

    # --- Serendipity sampling ---
    serendipity_pool = sources.get("serendipity_sources", [])
    n_serendipity = int(os.environ.get("SERENDIPITY_N", 3))
    sampled_serendipity = random.sample(serendipity_pool, min(n_serendipity, len(serendipity_pool)))
    if sampled_serendipity:
        logger.info(f"Serendipity sources sampled: {[s['name'] for s in sampled_serendipity]}")
        news_articles += fetch_rss_articles(sampled_serendipity)

    # Deduplicate news articles by URL (keep first occurrence)
    seen_urls: set[str] = set()
    unique_news: list = []
    for a in news_articles:
        if a.url not in seen_urls:
            seen_urls.add(a.url)
            unique_news.append(a)
    articles = unique_news

    # Deduplicate social posts by URL
    seen_social: set[str] = set()
    social_articles: list = []
    for a in raw_social:
        if a.url not in seen_social:
            seen_social.add(a.url)
            social_articles.append(a)

    logger.info(f"Total articles fetched: {len(articles)}, social posts: {len(social_articles)}")

    if not articles:
        logger.warning("No articles fetched — briefing will be empty")

    # --- Score + iterative quality pass ---
    max_iterations = int(os.environ.get("MAX_ITERATIONS", 3))
    tier1_threshold = int(os.environ.get("TIER1_THRESHOLD", 3))
    iterations_used = 1

    scoring_ok = True
    if not dry_run:
        articles, scoring_ok = score_articles(articles, profile)

        # Quality pass: if Tier 1 is sparse, fetch more from the remaining serendipity pool
        remaining_pool = [s for s in serendipity_pool if s not in sampled_serendipity]
        while scoring_ok and iterations_used < max_iterations:
            tier1_count = sum(1 for a in articles if a.tier == 1)
            if tier1_count >= tier1_threshold or not remaining_pool:
                break

            logger.info(
                f"Quality pass iteration {iterations_used + 1}: "
                f"Tier 1 count {tier1_count} < {tier1_threshold}, fetching more sources"
            )
            batch = remaining_pool[:5]
            remaining_pool = remaining_pool[5:]
            new_articles = fetch_rss_articles(batch)

            # Deduplicate new articles against what we already have
            new_articles = [a for a in new_articles if a.url not in seen_urls]
            for a in new_articles:
                seen_urls.add(a.url)

            if new_articles:
                new_articles, _ = score_articles(new_articles, profile)
                articles += new_articles

            iterations_used += 1

        if iterations_used > 1:
            logger.info(f"Quality pass completed after {iterations_used} iterations")

        executive_summary = generate_executive_summary(articles, profile)
        social_summary = generate_social_summary(social_articles, profile) if social_articles else ""
    else:
        logger.info("Dry run: skipping LLM scoring")
        for a in articles:
            a.tier = 2
            a.tier_reason = "(dry run)"
        executive_summary = "(dry run — no executive summary generated)"
        social_summary = ""

    # --- Format ---
    serendipity_names = [s["name"] for s in sampled_serendipity] if sampled_serendipity else None
    briefing_md = format_briefing(
        articles,
        executive_summary,
        profile,
        serendipity_names=serendipity_names,
        iterations_used=iterations_used,
        scoring_ok=scoring_ok,
        social_auth_failures=social_auth_failures if social_auth_failures else None,
        social_summary=social_summary if social_summary else None,
    )

    # --- Write output ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(ZoneInfo("Europe/Amsterdam")).strftime("%Y-%m-%d_%H%M")
    filename = f"briefing_{date_str}.md"
    output_path = OUTPUT_DIR / filename

    output_path.write_text(briefing_md, encoding="utf-8")
    logger.info(f"Briefing written to {output_path}")

    # Print path for CI visibility
    print(str(output_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM calls")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
