"""Discover and add RSS feeds for one or more website URLs.

Usage:
  python src/briefing/discover_source.py <url>
  python src/briefing/discover_source.py <url1>,<url2>,<url3>

Exit 0 if at least one feed was added.  Exit 1 if every URL failed.
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup
from openai import OpenAI

SOURCES_PATH = Path("config/sources.yaml")
# Use a real browser User-Agent so CDNs (Cloudflare, Fastly, etc.) don't
# block the request.  feedparser's default UA is often filtered.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}
REQUEST_TIMEOUT = 15


# ── HTTP + parse helpers ──────────────────────────────────────────────────────

def fetch_and_parse(url: str) -> "feedparser.FeedParserDict | None":
    """Fetch URL with requests (browser UA) and parse the content with feedparser."""
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS,
                         allow_redirects=True)
        if r.status_code != 200:
            return None
        return feedparser.parse(r.content)
    except Exception:
        return None


def is_valid_feed(url: str) -> bool:
    feed = fetch_and_parse(url)
    if feed is None:
        return False
    return bool(feed.entries) or bool(feed.feed.get("title"))


def get_feed_title(feed_url: str, fallback: str) -> str:
    feed = fetch_and_parse(feed_url)
    if feed is None:
        return fallback
    return feed.feed.get("title", "").strip() or fallback


# ── Discovery strategies ──────────────────────────────────────────────────────

def discover_via_html(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        for link in soup.find_all("link", rel="alternate"):
            link_type = link.get("type", "")
            if "rss" in link_type or "atom" in link_type:
                href = link.get("href", "").strip()
                if href:
                    found = urljoin(url, href)
                    print(f"  HTML autodiscovery candidate: {found}")
                    return found
    except Exception as exc:
        print(f"  HTML autodiscovery error: {exc}")
    return None


COMMON_FEED_SUFFIXES = [
    "/feed",
    "/feed.xml",
    "/feed.rss",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feeds/posts/default",
    "/blog/feed",
    "/news/feed",
    "/en/rss.xml",
]


def discover_via_common_paths(url: str) -> str | None:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Try suffixes on both the root domain and the given URL's path so that
    # e.g. https://example.com/the-batch also checks /the-batch/feed.xml.
    prefixes = [base]
    path = parsed.path.rstrip("/")
    if path:
        prefixes.append(base + path)

    seen: set[str] = set()
    for prefix in prefixes:
        for suffix in COMMON_FEED_SUFFIXES:
            candidate = prefix + suffix
            if candidate in seen:
                continue
            seen.add(candidate)
            print(f"  Trying: {candidate}")
            if is_valid_feed(candidate):
                return candidate
    return None


def try_url_variants(url: str) -> str | None:
    """Try the LLM-suggested URL and sensible variations (.xml, trailing slash, etc.)."""
    base = url.rstrip("/")
    variants = [url, base, base + ".xml", base + "/feed", base + "/feed.xml"]
    seen: set[str] = set()
    for v in variants:
        if v in seen:
            continue
        seen.add(v)
        print(f"  Trying variant: {v}")
        if is_valid_feed(v):
            return v
    return None


def discover_via_llm(url: str) -> tuple[str, str] | None:
    import json

    try:
        client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
        model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-6")

        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    f"You are an RSS feed discovery assistant.\n\n"
                    f"Website URL: {url}\n\n"
                    "Reply with ONLY a JSON object (no markdown, no explanation):\n"
                    '{"feed_url": "<most likely RSS/Atom feed URL — include full path '
                    'and .xml extension if applicable>", '
                    '"name": "<short descriptive source name>"}\n\n'
                    'If you cannot reasonably guess a feed URL, set "feed_url" to null.'
                ),
            }],
            temperature=0,
            max_tokens=200,
        )

        text = response.choices[0].message.content.strip()
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        data = json.loads(text)
        feed_url = data.get("feed_url")
        name = data.get("name", "")
        if feed_url:
            return feed_url, name
    except Exception as exc:
        print(f"  LLM error: {exc}")
    return None


# ── YAML append ───────────────────────────────────────────────────────────────

def append_to_sources(source_name: str, feed_url: str) -> None:
    content = SOURCES_PATH.read_text()

    name_scalar = yaml.dump(source_name, allow_unicode=True, default_flow_style=True).strip()
    url_scalar = yaml.dump(feed_url, allow_unicode=True, default_flow_style=True).strip()
    new_block = f"  - name: {name_scalar}\n    url: {url_scalar}\n"

    inserted = False
    for marker in ["social:", "web_sources:", "serendipity_sources:"]:
        pattern = f"\n{marker}"
        if pattern in content:
            content = content.replace(pattern, f"\n{new_block}{pattern[1:]}", 1)
            inserted = True
            break

    if not inserted:
        content = content.rstrip("\n") + "\n" + new_block

    SOURCES_PATH.write_text(content)


# ── Single-URL discovery pipeline ─────────────────────────────────────────────

def discover_one(url: str) -> tuple[str, str] | None:
    """Run the full discovery pipeline for one URL.
    Returns (feed_url, source_name) on success, None on failure.
    """
    feed_url: str | None = None
    source_name: str = ""

    print("\n[1/4] Checking if URL is already an RSS feed…")
    if is_valid_feed(url):
        feed_url = url
        print("  ✓ URL is already a valid feed.")

    if not feed_url:
        print("\n[2/4] Trying HTML autodiscovery…")
        feed_url = discover_via_html(url)
        if feed_url:
            print(f"  ✓ Found via HTML autodiscovery: {feed_url}")
        else:
            print("  No RSS link tag found.")

    if not feed_url:
        print("\n[3/4] Trying common feed paths…")
        feed_url = discover_via_common_paths(url)
        if feed_url:
            print(f"  ✓ Found via common path: {feed_url}")
        else:
            print("  No common path matched.")

    if not feed_url:
        print("\n[4/4] Asking LLM for a feed URL suggestion…")
        result = discover_via_llm(url)
        if result:
            candidate, llm_name = result
            print(f"  LLM suggested: {candidate}")
            validated = try_url_variants(candidate)
            if validated:
                feed_url = validated
                source_name = llm_name
                print(f"  ✓ Validated: {validated}")
            else:
                print("  ✗ Could not validate LLM suggestion.")
        else:
            print("  LLM returned no suggestion.")

    if not feed_url:
        return None

    if not source_name:
        source_name = get_feed_title(feed_url, fallback=urlparse(url).netloc)

    return feed_url, source_name


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: discover_source.py <url> [or comma-separated URLs]", file=sys.stderr)
        sys.exit(1)

    # Accept multiple URLs comma-separated (single arg) or as multiple args
    raw = ",".join(sys.argv[1:])
    urls = [u.strip() for u in re.split(r"[,\n]+", raw) if u.strip()]
    if not urls:
        print("No URLs provided.", file=sys.stderr)
        sys.exit(1)

    # Load existing feed URLs once to avoid duplicates within a batch
    existing = yaml.safe_load(SOURCES_PATH.read_text())
    existing_urls: set[str] = {
        s.get("url", "") for s in (existing.get("rss_feeds") or [])
    }

    succeeded, failed = 0, 0

    for i, url in enumerate(urls):
        print(f"\n{'=' * 60}")
        print(f"URL {i + 1}/{len(urls)}: {url}")

        result = discover_one(url)
        if result is None:
            print(f"✗ No RSS feed found for: {url}")
            failed += 1
            continue

        feed_url, source_name = result

        if feed_url in existing_urls:
            print(f"  Already in sources.yaml: {feed_url}")
            succeeded += 1
            continue

        append_to_sources(source_name, feed_url)
        existing_urls.add(feed_url)
        print(f'  ✓ Added "{source_name}" ({feed_url})')
        succeeded += 1

    print(f"\n{'=' * 60}")
    print(f"Summary: {succeeded} succeeded, {failed} failed out of {len(urls)} URL(s)")

    if succeeded == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
