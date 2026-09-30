from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class _FakeTools:
    """Minimal fake tools object exposing parse_actions used by filter_duplicates."""
    def parse_actions(self, pc):
        # Prefer explicit keys if provided by the test data for determinism
        if isinstance(pc, dict) and "thought" in pc and "action" in pc:
            return pc["thought"], pc["action"]
        # Fallback deterministic behavior
        text = pc.get("text", "") if isinstance(pc, dict) else str(pc)
        return text, text


class _FakeLogger:
    """Recorder for debug calls so tests can assert the debug branch was exercised."""
    def __init__(self):
        self.debug_calls = []

    def debug(self, msg, *args):
        # Record the message and the raw args tuple exactly as called
        self.debug_calls.append((msg, args))


def _make_instance(fake_tools, fake_logger):
    # Bypass __init__ to avoid requiring other project wiring; inject the two attributes used.
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._tools = fake_tools
    inst._logger = fake_logger
    return inst


def test_filter_duplicates_no_duplicates_round_029():
    """When all parsed actions are unique, filter_duplicates should return the original list
    and must not emit a debug call about filtering."""
    tools = _FakeTools()
    logger = _FakeLogger()
    sampler = _make_instance(tools, logger)

    completions = [
        {"thought": "first thought", "action": "action_one"},
        {"thought": "second thought", "action": "action_two"},
    ]

    result = sampler.filter_duplicates(completions)

    # Expect same objects and order when there are no duplicates
    assert result == completions
    assert result is not completions or result == completions  # deterministic equality check

    # The debug branch for filtering should not be called when nothing was removed
    assert logger.debug_calls == []


def test_filter_duplicates_with_duplicates_round_029():
    """When there are duplicate parsed actions, only the first occurrence is kept and a debug
    message is emitted describing the filtering from original -> filtered length."""
    tools = _FakeTools()
    logger = _FakeLogger()
    sampler = _make_instance(tools, logger)

    completions = [
        {"thought": "alpha", "action": "dup_action"},
        {"thought": "alpha-again", "action": "dup_action"},
        {"thought": "beta", "action": "unique_action"},
    ]

    result = sampler.filter_duplicates(completions)

    # Only the first occurrence of "dup_action" is kept along with the unique action
    assert result == [completions[0], completions[2]]
    assert len(result) == 2

    # The logger.debug should have been called once with the original and filtered lengths
    expected_msg = "Filtering duplicates: %d -> %d"
    # The code calls: self._logger.debug("Filtering duplicates: %d -> %d", len(completions), len(filtered_completions))
    assert logger.debug_calls == [(expected_msg, (3, 2))]
