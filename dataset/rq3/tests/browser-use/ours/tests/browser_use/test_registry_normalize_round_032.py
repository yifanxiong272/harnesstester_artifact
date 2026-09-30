import asyncio
import inspect
from typing import Optional

import pytest

from browser_use.tools.registry.service import Registry


def test_kwargs_not_allowed_round_032():
    """If the original function has **kwargs the normalizer must raise a ValueError."""
    registry = Registry()

    def fn_with_kwargs(a, **kwargs):
        return None

    with pytest.raises(ValueError, match=r"\*\*"):
        # normalization inspects signature and should reject **kwargs
        registry._normalize_action_function_signature(fn_with_kwargs, "desc", None)


def test_optional_special_param_conflict_round_032():
    """If a special parameter annotation is Optional[int] but expected type is str, normalizer raises a conflict error."""
    registry = Registry()

    # Patch the special param types to force a mismatch for page_extraction_llm
    def fake_specials():
        return {"page_extraction_llm": str}

    registry._get_special_param_types = fake_specials

    def action(page_extraction_llm: Optional[int]):
        return "ok"

    # The type normalization should detect Optional[int] vs expected str and raise
    with pytest.raises(ValueError, match=r"conflicts with special argument"):
        registry._normalize_action_function_signature(action, "desc", None)


def test_missing_browser_session_raises_round_032():
    """Calling the normalized wrapper with browser_session=None (required) must raise the specific ValueError."""
    registry = Registry()

    # Ensure the registry knows browser_session is a special parameter
    def fake_specials():
        return {"browser_session": None}

    registry._get_special_param_types = fake_specials

    # Define an action that requires browser_session as a positional param
    def action(browser_session):
        # If called correctly this would run; we expect the normalized wrapper to raise first
        return "ran"

    normalized, param_model = registry._normalize_action_function_signature(action, "desc", None)

    # Invoke the wrapper with browser_session explicitly set to None to trigger the branch
    with pytest.raises(ValueError, match=r"requires browser_session but none provided"):
        # normalized is async; run it deterministically
        asyncio.run(normalized(params=None, browser_session=None))
