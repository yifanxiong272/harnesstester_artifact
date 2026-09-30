import pytest

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyConfig:
    def __init__(self):
        # system_template is used directly as system_message
        self.system_template = "SYSTEM_MSG"
        # instance_template will be rendered with problem_statement and any extra fields, plus traj
        # use simple delimiters so result is easy to assert
        self.instance_template = "{{ problem_statement }}-{{ extra }}-{{ traj }}"
        # comparison_template uses the four named values passed to Template.render
        self.comparison_template = "{{ thought1 }}|{{ action1 }}|{{ thought2 }}|{{ action2 }}"


class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        # store debug messages so we can assert the debug calls happened (no external effect)
        self.messages.append(msg)


class DummyProblemStatement:
    def get_problem_statement(self):
        return "PS_TEXT"

    def get_extra_fields(self):
        return {"extra": "EXTRA"}


def make_comparator():
    cfg = DummyConfig()
    # model and tools are not used by format_messages; pass None
    comp = BinaryTrajectoryComparison(cfg, None, None)
    # Ensure debug logging calls are executed using our dummy logger
    comp._logger = DummyLogger()
    # Replace trajectory formatting to a deterministic return value to hit the trajectory-formatting call
    comp._format_trajectory = lambda traj: "FORMATTED_TRAJ"
    return comp


def test_format_messages_no_cache_round_053():
    """Exercise format_messages without cache_control to hit lines building templates and debug logging."""
    comp = make_comparator()

    ps = DummyProblemStatement()
    traj = [
        {"step": "irrelevant"}
    ]

    messages = comp.format_messages(
        problem_statement=ps,
        trajectory=traj,
        thought1="t1",
        action1="a1",
        thought2="t2",
        action2="a2",
        use_cache_control=False,
    )

    # Expect three messages: system, user (instance), user (comparison)
    assert isinstance(messages, list)
    assert len(messages) == 3

    # system message must be the system_template unchanged
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "SYSTEM_MSG"

    # instance user message content is a list with a single dict whose text is the rendered template
    instance_content = messages[1]["content"]
    assert isinstance(instance_content, list) and len(instance_content) == 1
    instance_item = instance_content[0]
    # The 'text' should be the rendered instance_template combining problem_statement, extra, and formatted trajectory
    assert instance_item["text"] == "PS_TEXT-EXTRA-FORMATTED_TRAJ"
    # When use_cache_control is False, there should be no 'cache_control' key in that dict
    assert "cache_control" not in instance_item

    # comparison message text should be rendered from comparison_template
    comparison_content = messages[2]["content"]
    assert isinstance(comparison_content, list) and len(comparison_content) == 1
    comparison_item = comparison_content[0]
    assert comparison_item["text"] == "t1|a1|t2|a2"

    # ensure that debug messages were emitted for system, instance, and comparison
    # There should be at least three debug messages recorded by our DummyLogger
    assert len(comp._logger.messages) >= 3


def test_format_messages_with_cache_round_053():
    """Exercise format_messages with cache_control True to hit the conditional branch adding cache_control kwargs."""
    comp = make_comparator()

    ps = DummyProblemStatement()
    traj = []

    messages = comp.format_messages(
        problem_statement=ps,
        trajectory=traj,
        thought1="X",
        action1="Y",
        thought2="Z",
        action2="W",
        use_cache_control=True,
    )

    # Validate structure again
    assert len(messages) == 3

    # Now the instance content dict should include cache_control with the expected ephemeral type
    instance_item = messages[1]["content"][0]
    assert instance_item["text"] == "PS_TEXT-EXTRA-FORMATTED_TRAJ"
    assert "cache_control" in instance_item
    assert instance_item["cache_control"] == {"type": "ephemeral"}

    # And the comparison rendering should reflect the provided values
    assert messages[2]["content"][0]["text"] == "X|Y|Z|W"
