#!/usr/bin/env python3
from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from common.model_settings import message_content as message_content
from common.model_settings import parse_env_file

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
RETRYABLE_HTTP_STATUS = {408, 409, 425, 429}


def is_retryable_http_status(status: int) -> bool:
    return status >= 500 or status in RETRYABLE_HTTP_STATUS


def load_env(*paths: Path | None) -> dict[str, str]:
    env = os.environ.copy()
    for path in paths:
        if path is not None:
            env.update(parse_env_file(path))
    return env


def provider_access(provider: str, env: dict[str, str]) -> tuple[str, str]:
    """Return the configured API key and base URL for one supported provider."""

    if provider == "openai":
        key = env.get("OPENAI_API_KEY") or env.get("LLM_API_KEY")
        base_url = env.get("OPENAI_BASE_URL") or env.get(
            "LLM_BASE_URL", OPENAI_BASE_URL
        )
    elif provider == "openrouter":
        key = env.get("OPENROUTER_API_KEY") or env.get("LLM_API_KEY")
        base_url = env.get("OPENROUTER_BASE_URL") or env.get(
            "LLM_BASE_URL", OPENROUTER_BASE_URL
        )
    else:
        raise SystemExit(f"unsupported model provider: {provider}")
    if not key:
        raise SystemExit(f"missing API key for model provider: {provider}")
    return key, base_url


def chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str,
    env: dict[str, str],
    provider: str = "openrouter",
    timeout: int = 120,
    retries: int = 4,
) -> dict[str, Any]:
    key, base_url = provider_access(provider, env)
    conversation = list(messages)
    if not conversation or conversation[0].get("role") != "system":
        conversation.insert(
            0,
            {
                "role": "system",
                "content": "Return only valid JSON that matches the requested schema.",
            },
        )
    payload = {
        "model": model,
        "messages": conversation,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_error: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if not is_retryable_http_status(exc.code):
                raise
            last_error = exc
        except (TimeoutError, http.client.HTTPException, urllib.error.URLError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(min(8.0, 1.5 * (attempt + 1)))
    if last_error is None:
        raise RuntimeError("model request retry loop did not execute")
    raise last_error
