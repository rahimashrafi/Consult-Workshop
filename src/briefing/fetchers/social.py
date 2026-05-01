"""
Social media fetcher via RSSHub.

RSSHub converts Twitter/X profiles into RSS feeds without requiring an API key.
Public instance: https://rsshub.app — reliable for small-scale use.
For production reliability, consider self-hosting: https://docs.rsshub.app/deploy/

HTTP 401/403 responses indicate the RSSHub instance's OAuth token has expired and
needs renewal; these are surfaced separately so the briefing can warn the user.
Other failures (network, rate-limit, etc.) are skipped silently.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

import feedparser
import httpx

from ..models import Article

logger = logging.getLogger(__name__)

LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", 25))


def _rsshub_url(instance: str, handle: str) -> str:
    instance = instance.rstrip("/")
    return f"{instance}/twitter/user/{handle}"


def _parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        raw = getattr(entry, attr, None)
        if raw:
            return datetime(*raw[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_social_articles(social_config: dict) -> tuple[list[Article], list[str]]:
    """Return (articles, auth_failed_handles).

    auth_failed_handles contains handles that returned HTTP 401/403, indicating
    the RSSHub OAuth token needs renewal.
    """
    instance = (
        os.environ.get("RSSHUB_INSTANCE")
        or social_config.get("rsshub_instance", "https://rsshub.app")
    )
    accounts = social_config.get("twitter_accounts") or []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles: list[Article] = []
    auth_failed_handles: list[str] = []

    for account in accounts:
        handle = account["handle"]
        url = _rsshub_url(instance, handle)
        try:
            response = httpx.get(url, timeout=15, follow_redirects=True, headers={
                "User-Agent": "ConsultBot/1.0"
            })
            response.raise_for_status()
            parsed = feedparser.parse(response.text)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.warning(
                    f"Social auth error for @{handle}: HTTP {e.response.status_code} "
                    f"— RSSHub token needs renewal"
                )
                auth_failed_handles.append(handle)
            else:
                logger.warning(f"Social fetch failed for @{handle}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Social fetch failed for @{handle}: {e}")
            continue

        for entry in parsed.entries:
            pub = _parse_date(entry)
            if pub < cutoff:
                continue

            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()

            if not title:
                continue

            articles.append(Article(
                title=f"@{handle}: {title[:200]}",
                url=link or f"https://twitter.com/{handle}",
                source_name=account.get("name", f"@{handle}"),
                category="social",
                language="en",
                published=pub,
                summary=summary[:600],
            ))

    logger.info(f"Social fetcher: {len(articles)} posts from {len(accounts)} accounts")
    return articles, auth_failed_handles
