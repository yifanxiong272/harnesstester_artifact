from types import SimpleNamespace
from browser_use.llm.openai.chat import ChatOpenAI


def _make_fake_response(completion_tokens: int, reasoning_tokens: int) -> SimpleNamespace:
    """Create a minimal ChatCompletion-like object matching attributes used by _get_usage.

    Structure mirrors: response.usage.{prompt_tokens, prompt_tokens_details, completion_tokens, completion_tokens_details, total_tokens}
    """
    prompt_tokens_details = SimpleNamespace(cached_tokens=0)
    completion_tokens_details = SimpleNamespace(reasoning_tokens=reasoning_tokens)
    usage = SimpleNamespace(
        prompt_tokens=1,
        prompt_tokens_details=prompt_tokens_details,
        completion_tokens=completion_tokens,
        completion_tokens_details=completion_tokens_details,
        total_tokens=1,
    )
    response = SimpleNamespace(usage=usage)
    return response


def test_probe_001_nonnegative_completion_tokens_after_reasoning_addition():
    """Probe: ensure completion_tokens is non-negative even when reasoning_tokens is negative.

    This test constructs a response whose completion_tokens=5 and reasoning_tokens=-10 and
    calls the target method to observe whether the result enforces non-negativity.
    """
    # deterministic inputs per boundary plan
    response = _make_fake_response(completion_tokens=5, reasoning_tokens=-10)

    # Create a ChatOpenAI instance without running its initializer; _get_usage does not use self state.
    ai = object.__new__(ChatOpenAI)

    # Call the target method (as allowed by the boundary plan activation). This exercises the
    # exact implementation under test and yields a ChatInvokeUsage-like object or None.
    result = ai._get_usage(response)

    # The independent semantic invariant: token counts are counts and must be non-negative integers.
    assert result is not None, "expected usage to be present when response.usage is provided"

    # Primary oracle: completion_tokens must be a non-negative integer.
    # Use a conservative check: it's an int-like and >= 0.
    comp = getattr(result, "completion_tokens", None)
    assert isinstance(comp, int), f"completion_tokens should be int-like, got: {type(comp)!r}"
    assert comp >= 0, f"completion_tokens must be non-negative but was {comp} (completion_tokens + reasoning_tokens may have underflowed)"
