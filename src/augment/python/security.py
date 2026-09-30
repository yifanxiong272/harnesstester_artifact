from __future__ import annotations

import re


SENSITIVE_ENV_KEY_PATTERN = (
    r"(?:^|_)(?:API_KEY|AUTH|KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?|PRIVATE_KEY)"
    r"(?:_|$)"
)
_SENSITIVE_ENV_KEY = re.compile(SENSITIVE_ENV_KEY_PATTERN, re.IGNORECASE)


def sensitive_env_key(key: str) -> bool:
    """Return whether a subprocess environment key can carry credentials."""

    return bool(_SENSITIVE_ENV_KEY.search(key))
