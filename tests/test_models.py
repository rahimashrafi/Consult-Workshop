"""
Validates that each model in the dashboard's MODELS list is reachable via OpenRouter
and returns a parseable scoring response.

Run:
    OPENROUTER_API_KEY=sk-... python -m pytest tests/test_models.py -v
Or standalone:
    OPENROUTER_API_KEY=sk-... python tests/test_models.py
"""

import os
import sys

from openai import OpenAI

MODELS = [
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-haiku-4.5",
    "qwen/qwen3.6-plus",
    "google/gemma-4-31b-it",
    "openai/gpt-oss-safeguard-20b:nitro",
    "deepseek/deepseek-v4-flash",
    "deepseek/deepseek-v3.2",
]

PROBE_PROMPT = (
    "Reply with a JSON object with a single key 'tier' set to the integer 2. "
    "No markdown, no explanation — only the JSON object."
)


def check_model(client: OpenAI, model_id: str) -> tuple[bool, str]:
    """Return (ok, detail). ok=True means the model accepted the call and returned parseable output."""
    import json

    try:
        resp = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": PROBE_PROMPT}],
            max_tokens=32,
            temperature=0,
        )
    except Exception as e:
        return False, f"API error: {e}"

    content = (resp.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(content)
        if "tier" not in parsed:
            return False, f"Unexpected JSON (no 'tier' key): {content!r}"
        return True, f"tier={parsed['tier']}"
    except json.JSONDecodeError:
        return False, f"Non-JSON response: {content!r}"


def run():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    results = []
    for model_id in MODELS:
        ok, detail = check_model(client, model_id)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {model_id:<45} {detail}")
        results.append(ok)

    failures = results.count(False)
    print(f"\n{len(MODELS) - failures}/{len(MODELS)} models passed.")
    if failures:
        sys.exit(1)


# ── pytest integration ────────────────────────────────────────────────────────

import pytest


@pytest.fixture(scope="module")
def client():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


@pytest.mark.parametrize("model_id", MODELS)
def test_model_returns_score(client, model_id):
    ok, detail = check_model(client, model_id)
    assert ok, f"{model_id} failed: {detail}"


if __name__ == "__main__":
    run()
