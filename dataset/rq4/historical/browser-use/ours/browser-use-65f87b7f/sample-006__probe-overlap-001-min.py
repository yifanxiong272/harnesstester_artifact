from browser_use.agent.views import AgentHistory


def test_probe_001():
    def make_dummy_action(text: str):
        class DummyAction:
            def model_dump(self, exclude_none=True, mode='json'):
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

    raw_short = "abc"
    raw_long = "XabcY"
    mixed_text = "start " + raw_long + " " + raw_short + " " + raw_long + raw_short + " end"

    model_output_obj = DummyModelOutput([make_dummy_action(mixed_text)])
    ah = AgentHistory.model_construct(
        model_output=model_output_obj,
        result=[DummyResult()],
        state=DummyState(),
        metadata=None,
        state_message="test",
    )

    sensitive_data = {
        "k_short": raw_short,
        "domain": {"k_long": raw_long},
    }

    dumped = ah.model_dump(sensitive_data=sensitive_data)

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

    for s in iter_strings(dumped):
        assert raw_short not in s, f"raw short secret '{raw_short}' remains in output string: {s!r}"
        assert raw_long not in s, f"raw long secret '{raw_long}' remains in output string: {s!r}"
        if "<secret>k_short</secret>" in s:
            found_placeholder_short = True
        if "<secret>k_long</secret>" in s:
            found_placeholder_long = True

    assert found_placeholder_short, "Did not find placeholder '<secret>k_short</secret>' in dumped output"
    assert found_placeholder_long, "Did not find placeholder '<secret>k_long</secret>' in dumped output"
