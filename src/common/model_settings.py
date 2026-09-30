"""Shared environment-file and response decoding for Python model clients."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_env_file(path: Path) -> dict[str, str]:
    """Read shell-style assignments without executing them."""
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def message_content(response: dict[str, Any]) -> str:
    """Return the first assistant message content as text."""
    choices = response.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    return content if isinstance(content, str) else json.dumps(content)
