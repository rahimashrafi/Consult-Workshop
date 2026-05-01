"""
LLM processor: scores articles by relevance to the active report profile,
then generates a short executive summary for Tier 1 items.

All articles are batched into a single prompt to keep API costs minimal.
Estimated cost: ~€0.05–0.10 per daily run with Claude Sonnet 4.6.
"""

import json
import logging
import os
from textwrap import dedent

from openai import OpenAI

from .models import Article

logger = logging.getLogger(__name__)


def _build_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set — LLM calls will be skipped")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


def _article_block(idx: int, article: Article) -> str:
    return dedent(f"""\
        [{idx}]
        Title: {article.title}
        Source: {article.source_name} ({article.category})
        Summary: {article.summary or '(no summary available)'}
    """)


def score_articles(articles: list[Article], profile: dict) -> tuple[list[Article], bool]:
    """Return (articles, scoring_ok). scoring_ok is False when the LLM call failed."""
    if not articles:
        return articles, True

    try:
        model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
        client = _build_client()

        report = profile["report"]
        tiers = profile["relevance_tiers"]

        system_prompt = dedent(f"""\
            You are a research assistant helping a policy analyst at a central bank.
            The analyst is writing a report titled: "{report['title_en']}"
            Perspective: {report['perspective']}

            Report focus:
            {profile['core_focus']}

            Key themes:
            {chr(10).join(f'- {t}' for t in profile['themes'])}

            Key actors:
            {chr(10).join(f'- {a}' for a in profile['key_actors'])}

            Relevance tiers — assign EXACTLY one tier to each article:
            - Tier 0 "{tiers['tier_0']['label']}": {tiers['tier_0']['description']}
            - Tier 1 "{tiers['tier_1']['label']}": {tiers['tier_1']['description']}
            - Tier 2 "{tiers['tier_2']['label']}": {tiers['tier_2']['description']}
            - Tier 3 "{tiers['tier_3']['label']}": {tiers['tier_3']['description']}

            When uncertain between Tier 0 and Tier 3, assign Tier 3 — Tier 0 is only
            for content with no policy or economic angle whatsoever. Tier 3 is available
            for any source type; it is not reserved for institutional sources.
        """)

        article_text = "\n".join(_article_block(i, a) for i, a in enumerate(articles))

        user_prompt = dedent(f"""\
            Below are {len(articles)} news items.
            Assign each a tier (0, 1, 2, or 3) and provide a brief reason (1 sentence)
            written for the analyst — explain specifically why this article is or isn't
            relevant to the report, referencing the theme or actor it relates to where
            possible. Do not write generic reasons like "this article is about AI."

            Respond ONLY with valid JSON — an array with one object per article, in the same order:
            [
              {{"index": 0, "tier": 1, "reason": "..."}},
              ...
            ]

            Articles:
            {article_text}
        """)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or ""
        logger.debug(f"Scoring raw response (first 200 chars): {raw[:200]!r}")
        # Strip markdown code fences that some models add despite json_object mode
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.rsplit("```", 1)[0].strip()
        # The model may wrap the array in a key; handle both formats
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            parsed = next(iter(parsed.values()))

        for item in parsed:
            idx = item["index"]
            if 0 <= idx < len(articles):
                articles[idx].tier = int(item.get("tier", 3))
                articles[idx].tier_reason = item.get("reason", "")
        return articles, True
    except EnvironmentError as e:
        logger.warning(f"LLM scoring skipped: {e}")
        for a in articles:
            if a.tier == 0:
                a.tier = 3
                a.tier_reason = "Scoring unavailable (API key not set)"
        return articles, False
    except Exception as e:
        error_type = type(e).__name__
        raw_snippet = locals().get("raw", "")
        if raw_snippet:
            logger.error(f"LLM scoring failed [{error_type}]: {e}\nRaw response (first 500 chars): {str(raw_snippet)[:500]}")
        else:
            logger.error(f"LLM scoring failed [{error_type}]: {e}")
        for a in articles:
            if a.tier == 0:
                a.tier = 3
                a.tier_reason = f"Scoring unavailable ({error_type})"
        return articles, False


def generate_social_summary(social_articles: list[Article], profile: dict) -> str:
    """Generate a thematic summary of what followed social accounts are discussing."""
    if not social_articles:
        return ""

    try:
        model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
        client = _build_client()
        report = profile["report"]

        posts_text = "\n".join(
            f"- [{a.source_name}]({a.url}) ({a.published.strftime('%H:%M')}): "
            f"{a.summary or a.title}"
            for a in sorted(social_articles, key=lambda x: x.published, reverse=True)
        )

        system_msg = dedent(f"""\
            You are summarizing what AI/policy/tech experts are discussing on social media.
            The reader is a senior policy analyst at {report['perspective']},
            writing a report on: "{report['title_en']}"
            Write concisely in English. Use markdown formatting.
        """)

        user_msg = dedent(f"""\
            Below are posts from the past 24 hours by AI, policy, and tech experts.

            Identify 2-4 themes or discussions these experts are engaging with.
            For each theme:
            - Write a 1-2 sentence description in English of what's being discussed
            - Name the specific people contributing, linking their name to the post: [Name](url)
            - Skip purely personal content or posts with no policy/economic angle

            Focus on themes relevant to AI policy, EU regulation, startup ecosystems,
            or central bank/economic perspectives. If fewer than 2 meaningful themes exist,
            write one short paragraph.

            Do not include a header — just the content.

            Posts:
            {posts_text}
        """)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Social summary generation failed: {e}")
        return ""


def generate_executive_summary(articles: list[Article], profile: dict) -> str:
    """Generate a 3–5 sentence executive summary for Tier 1 articles."""
    tier1 = [a for a in articles if a.tier == 1]
    if not tier1:
        return ""

    try:
        model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")
        client = _build_client()
        report = profile["report"]

        items_text = "\n".join(
            f"- {a.title} ({a.source_name}): {a.summary}" for a in tier1
        )

        system_msg = dedent(f"""\
            You are briefing a senior policy analyst at {report['perspective']}.
            They are writing a report on: "{report['title_en']}"
            Write in a direct, analytical tone suitable for a central bank analyst. Be in English.
        """)

        user_msg = dedent(f"""\
            These are today's most directly relevant news items:
            {items_text}

            Write a concise executive summary (no bullet points) that:
            - Opens with the most substantive finding, not a scene-setting sentence
            - Highlights the most important developments
            - Notes any patterns or connections between items
            - Cites the source organisation by name when it strengthens the point
              (e.g. "The OECD noted..." or "According to the report data...")
            - Scales length to the material: 2–3 sentences if there is only one item,
              up to 5 sentences for a busy news day with many items

            Do not start with "Today" or repeat the report title.
        """)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Executive summary generation failed: {e}")
        return ""
