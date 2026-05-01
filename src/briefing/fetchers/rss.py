import feedparser
import httpx
import logging
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from ..models import Article

logger = logging.getLogger(__name__)

LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", 25))


def _parse_date(entry) -> datetime | None:
    for attr in ("published", "updated"):
        raw = getattr(entry, f"{attr}_parsed", None)
        if raw:
            import time
            return datetime(*raw[:6], tzinfo=timezone.utc)
        raw_str = getattr(entry, attr, None)
        if raw_str:
            try:
                return parsedate_to_datetime(raw_str).astimezone(timezone.utc)
            except Exception:
                pass
    return None


def _fetch_feed(url: str) -> feedparser.FeedParserDict | None:
    try:
        response = httpx.get(url, timeout=15, follow_redirects=True, headers={
            "User-Agent": "ConsultBot/1.0 (policy research briefing agent)"
        })
        response.raise_for_status()
        return feedparser.parse(response.text)
    except Exception as e:
        logger.warning(f"Failed to fetch RSS {url}: {e}")
        return None


def fetch_rss_articles(feed_configs: list[dict]) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles: list[Article] = []

    for feed in feed_configs:
        parsed = _fetch_feed(feed["url"])
        if not parsed:
            continue

        for entry in parsed.entries:
            pub = _parse_date(entry)
            if pub is None:
                # No date — include anyway and let the LLM decide
                pub = datetime.now(timezone.utc)
            if pub < cutoff:
                continue

            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue

            summary = (
                entry.get("summary", "")
                or entry.get("description", "")
            ).strip()
            # Strip HTML tags from summary
            summary = _strip_html(summary)[:600]

            articles.append(Article(
                title=title,
                url=url,
                source_name=feed["name"],
                category=feed.get("category", "general"),
                language=feed.get("language", "en"),
                published=pub,
                summary=summary,
            ))

    logger.info(f"RSS fetcher: {len(articles)} articles from {len(feed_configs)} feeds")
    return articles


def _strip_html(text: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(text, "lxml").get_text(separator=" ").strip()
