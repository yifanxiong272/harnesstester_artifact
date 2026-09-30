from browser_use.agent.views import AgentHistory


def test_probe_001():
    """Probe overlapping sensitive-value replacement ordering via AgentHistory.model_dump.

    Constructs a minimal AgentHistory instance via AgentHistory.model_construct and a synthetic
    model_output.action whose model_dump returns an 'input' dict with a text field containing
    multiple occurrences of two overlapping secrets (short='abc', long='XabcY'). The sensitive_data
    mapping intentionally inserts the short secret first (old-format top-level entry) and the
    longer secret second (new-format nested dict) so the target's insertion-order replacement
    behavior is exercised.
    """

    # Local helpers to build minimal compatible pieces expected by model_dump
    def make_dummy_action(text: str):
        class DummyAction:
            def model_dump(self, exclude_none=True, mode='json'):
                # Return a structure that will be recognized as an action with an 'input'
                return {"input": {"text": text}}

        return DummyAction()

    class DummyModelOutput:
        def __init__(self, action_list):
            self.evaluation_previous_goal = "prev"
            self.memory = "mem"
            self.next_goal = "next"
            self.action = action_list
            self.thinking = None
            self.current_plan_item = None
            self.plan_update = None

    class DummyResult:
        def model_dump(self, exclude_none=True, mode='json'):
            return {}

    class DummyState:
        def to_dict(self):
            return {}

    # Build the test string containing multiple and overlapping occurrences in mixed orders
    raw_short = "abc"
    raw_long = "XabcY"
    mixed_text = "start " + raw_long + " " + raw_short + " " + raw_long + raw_short + " end"

    # Create AgentHistory instance using pydantic's model_construct to avoid BaseModel __setattr__ side effects
    model_output_obj = DummyModelOutput([make_dummy_action(mixed_text)])
    ah = AgentHistory.model_construct(
        model_output=model_output_obj,
        result=[DummyResult()],
        state=DummyState(),
        metadata=None,
        state_message="test",
    )

    # sensitive_data mapping: place the short secret first (old-format entry), then the long secret
    sensitive_data = {
        # old-format top-level entry -> will be inserted into sensitive_values as key 'k_short'
        "k_short": raw_short,
        # new-format nested dict -> inner key k_long will be inserted after k_short
        "domain": {"k_long": raw_long},
    }

    # Invoke the public entrypoint; this should route strings through _filter_sensitive_data_from_string
    dumped = ah.model_dump(sensitive_data=sensitive_data)

    # Recursive string walker to examine all returned strings deterministically
    def iter_strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from iter_strings(v)
        elif isinstance(obj, (list, tuple, set)):
            for v in obj:
                yield from iter_strings(v)
        else:
            return

    found_placeholder_short = False
    found_placeholder_long = False

    # Primary assertions: no raw secret substrings remain anywhere; placeholders for both keys must exist
    for s in iter_strings(dumped):
        # Conservative public invariant: no raw sensitive substrings remain in any returned string
        assert raw_short not in s, f"raw short secret '{raw_short}' remains in output string: {s!r}"
        assert raw_long not in s, f"raw long secret '{raw_long}' remains in output string: {s!r}"
        if "<secret>k_short</secret>" in s:
            found_placeholder_short = True
        if "<secret>k_long</secret>" in s:
            found_placeholder_long = True

    # Ensure both placeholders were emitted at least once
    assert found_placeholder_short, "Did not find placeholder '<secret>k_short</secret>' in dumped output"
    assert found_placeholder_long, "Did not find placeholder '<secret>k_long</secret>' in dumped output"
