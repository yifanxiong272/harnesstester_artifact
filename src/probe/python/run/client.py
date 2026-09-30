#!/usr/bin/env python3
"""Minimal chat-completions client used by target-probing workflows."""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from common.model_settings import message_content as message_content, parse_env_file
from probe.python.run.deadline import limit_timeout

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"


class LLMHTTPError(RuntimeError):
    def __init__(self, exc: urllib.error.HTTPError, body: str = "") -> None:
        suffix = f": {body[:1000]}" if body else ""
        super().__init__(f"HTTP Error {exc.code}: {exc.reason}{suffix}")
        self.code = exc.code
        self.reason = exc.reason
        self.body = body


def load_env(*paths: Path) -> dict[str, str]:
    """Overlay env-file values on the current process environment."""

    env = os.environ.copy()
    for path in paths:
        env.update(parse_env_file(path))
    return env


def chat_completion(
    *,
    prompt: str,
    model: str,
    env: dict[str, str],
    provider: str = "openrouter",
    timeout: int = 120,
    retries: int = 5,
) -> dict[str, Any]:
    """Call the selected provider and return the raw chat-completion payload."""

    if provider == "openai":
        key = env.get("OPENAI_API_KEY") or env.get("LLM_API_KEY")
        base_url = env.get("OPENAI_BASE_URL", OPENAI_BASE_URL)
    elif provider == "openrouter":
        key = env.get("OPENROUTER_API_KEY") or env.get("LLM_API_KEY")
        base_url = env.get("OPENROUTER_BASE_URL") or env.get(
            "LLM_BASE_URL", OPENROUTER_BASE_URL
        )
    else:
        raise SystemExit(f"unsupported model provider: {provider}")
    if not key:
        raise SystemExit(f"missing API key for model provider: {provider}")
    payload = {
        "model": provider_model_name(provider, model),
        "messages": [
            {
                "role": "system",
                "content": "Return only valid JSON that matches the requested schema.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    last_error: BaseException | None = None
    for attempt in range(retries + 1):
        limit_timeout()
        request = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=limit_timeout(timeout)
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
                limit_timeout()
                return result
        except urllib.error.HTTPError as exc:
            if exc.code < 500 and exc.code not in {408, 409, 425, 429}:
                raise LLMHTTPError(exc, read_error_body(exc)) from exc
            last_error = exc
        except (TimeoutError, http.client.HTTPException, urllib.error.URLError) as exc:
            last_error = exc
        limit_timeout()
        if attempt < retries:
            time.sleep(limit_timeout(retry_delay(attempt=attempt, error=last_error)))
            limit_timeout()
    assert last_error is not None
    raise last_error


def retry_delay(*, attempt: int, error: BaseException | None) -> float:
    """Back off transient provider/network failures without spending sample budget."""

    retry_after = retry_after_seconds(error)
    if retry_after is not None:
        return min(60.0, retry_after)
    return min(30.0, 2.0 * (2**attempt))


def retry_after_seconds(error: BaseException | None) -> float | None:
    if not isinstance(error, urllib.error.HTTPError):
        return None
    headers = getattr(error, "headers", None)
    value = headers.get("Retry-After") if headers else None
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def provider_model_name(provider: str, model: str) -> str:
    """Translate wrapper model names to provider-specific model names."""

    if provider == "openai" and model.startswith("openai/"):
        return model.split("/", 1)[1]
    return model


def read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
