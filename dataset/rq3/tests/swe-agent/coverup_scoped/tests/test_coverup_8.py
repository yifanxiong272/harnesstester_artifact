# file: sweagent/agent/action_sampler.py:164-209
# asked: {"lines": [175, 176, 177, 178, 179, 181, 182, 183, 185, 186, 187, 188, 189, 190, 192, 193, 194, 195, 196, 197, 198, 200, 201, 202, 203, 204, 205], "branches": []}
# gained: {"lines": [175, 176, 177, 178, 179, 181, 182, 183, 185, 186, 187, 188, 189, 190, 192, 193, 194, 195, 196, 197, 198, 200, 201, 202, 203, 204, 205], "branches": []}

import pytest
from types import SimpleNamespace

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyLogger:
    def __init__(self):
        self.debug_messages = []

    def debug(self, msg):
        # store debug messages for later assertions
        self.debug_messages.append(msg)


class DummyProblemStatement:
    def get_problem_statement(self):
        return "PROBLEM_STATEMENT_TEXT"

    def get_extra_fields(self):
        return {"extra_field": "EXTRA_VALUE"}


class DummyBinaryTrajectoryComparison(BinaryTrajectoryComparison):
    def __init__(self, system_template, instance_template, comparison_template):
        # do not call super().__init__; just set what format_messages needs
        self.config = SimpleNamespace(
            system_template=system_template,
            instance_template=instance_template,
            comparison_template=comparison_template,
        )
        self._logger = DummyLogger()

    def _format_trajectory(self, trajectory):
        # return a deterministic string for assertions
        return "FORMATTED_TRAJ:" + ",".join(str(x) for x in (trajectory or []))


def _call_format_messages(use_cache_control: bool):
    system_template = "SYSTEM TEMPLATE CONTENT"
    instance_template = "{{problem_statement}}||{{extra_field}}||{{traj}}"
    comparison_template = "TH1={{thought1}};A1={{action1}}||TH2={{thought2}};A2={{action2}}"

    sampler = DummyBinaryTrajectoryComparison(
        system_template=system_template,
        instance_template=instance_template,
        comparison_template=comparison_template,
    )

    ps = DummyProblemStatement()
    trajectory = ["step1", "step2"]

    msgs = sampler.format_messages(
        problem_statement=ps,
        trajectory=trajectory,
        thought1="think1",
        action1="act1",
        thought2="think2",
        action2="act2",
        use_cache_control=use_cache_control,
    )

    return sampler, msgs


def test_format_messages_without_cache_control():
    sampler, msgs = _call_format_messages(use_cache_control=False)

    # Expect three messages returned
    assert isinstance(msgs, list)
    assert len(msgs) == 3

    # First message: system
    sys_msg = msgs[0]
    assert sys_msg["role"] == "system"
    assert sys_msg["content"] == "SYSTEM TEMPLATE CONTENT"

    # Second message: user instance with a list content containing a dict with text but no cache_control
    inst_msg = msgs[1]
    assert inst_msg["role"] == "user"
    assert isinstance(inst_msg["content"], list) and len(inst_msg["content"]) == 1
    inst_content = inst_msg["content"][0]
    assert inst_content["type"] == "text"
    # As use_cache_control is False, there should be no cache_control key
    assert "cache_control" not in inst_content
    # Check the rendered instance template substituted problem_statement, extra_field, and trajectory
    expected_user_text = "PROBLEM_STATEMENT_TEXT||EXTRA_VALUE||FORMATTED_TRAJ:step1,step2"
    assert inst_content["text"] == expected_user_text

    # Third message: user comparison with nested list content containing a dict with the comparison text
    comp_msg = msgs[2]
    assert comp_msg["role"] == "user"
    assert isinstance(comp_msg["content"], list) and len(comp_msg["content"]) == 1
    comp_content = comp_msg["content"][0]
    assert comp_content["type"] == "text"
    expected_comp_text = "TH1=think1;A1=act1||TH2=think2;A2=act2"
    assert comp_content["text"] == expected_comp_text

    # Verify that logger debug was called for system, instance, and comparison inputs (three calls)
    # The debug messages should contain substrings of the content
    dbg = sampler._logger.debug_messages
    assert any("MODEL INPUT (system)" in m for m in dbg)
    assert any("MODEL INPUT (instance)" in m for m in dbg)
    assert any("MODEL INPUT (comparison)" in m for m in dbg)


def test_format_messages_with_cache_control():
    sampler, msgs = _call_format_messages(use_cache_control=True)

    # First user message (instance) should include cache_control in its content dict
    inst_content = msgs[1]["content"][0]
    assert inst_content["type"] == "text"
    assert "cache_control" in inst_content
    assert inst_content["cache_control"] == {"type": "ephemeral"}

    # Comparison message should NOT include cache_control (only the instance message gets it)
    comp_content = msgs[2]["content"][0]
    assert comp_content["type"] == "text"
    assert "cache_control" not in comp_content

    # Ensure texts still rendered correctly
    assert inst_content["text"].startswith("PROBLEM_STATEMENT_TEXT||EXTRA_VALUE||FORMATTED_TRAJ:")
    assert comp_content["text"] == "TH1=think1;A1=act1||TH2=think2;A2=act2"
