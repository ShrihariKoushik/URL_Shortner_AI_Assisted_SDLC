"""Minimal OpenAI helper for engineer-led requirement understanding.

This wraps a single Chat Completions call that returns a JSON object. It is used
as an *accelerator* for the engineer: the engineer still reviews, edits, or
rejects the suggestion, and a deterministic local fallback runs whenever no key
is configured or the call fails.
"""

import json
from urllib import error, request

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def call_openai_json(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    base_url: str = OPENAI_URL,
    timeout: int = 45,
) -> dict[str, object]:
    """Call OpenAI and return a parsed JSON object. Raises on any failure."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:  # noqa: S310 (trusted host)
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    return _parse_json_object(content)


def _parse_json_object(content: str) -> dict[str, object]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("AI response must be a JSON object")
    return parsed


OPENAI_ERRORS = (OSError, KeyError, json.JSONDecodeError, error.HTTPError, TypeError, ValueError)
