# file: sweagent/agent/action_sampler.py:164-209
# asked: {"lines": [175, 176, 177, 178, 179, 181, 182, 183, 185, 186, 187, 188, 189, 190, 192, 193, 194, 195, 196, 197, 198, 200, 201, 202, 203, 204, 205], "branches": []}
# gained: {"lines": [175, 176, 177, 178, 179, 181, 182, 183, 185, 186, 187, 188, 189, 190, 192, 193, 194, 195, 196, 197, 198, 200, 201, 202, 203, 204, 205], "branches": []}

import types
import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        self.messages.append(msg)


class DummyProblemStatement:
    def __init__(self, ps_text="PS", extra=None):
        self._ps = ps_text
        self._extra = {} if extra is None else extra

    def get_problem_statement(self):
        return self._ps

    def get_extra_fields(self):
        return self._extra


def make_instance(system_template, instance_template, comparison_template, formatted_traj="TRAJ"):
    # Create a bare instance without calling __init__ to avoid side-effects
    inst = object.__new__(BinaryTrajectoryComparison)
    inst.config = types.SimpleNamespace(
        system_template=system_template,
        instance_template=instance_template,
        comparison_template=comparison_template,
    )
    inst._format_trajectory = lambda traj: formatted_traj
    inst._logger = DummyLogger()
    return inst


def test_format_messages_without_cache_control():
    system_template = "SYSTEM_MSG"
    instance_template = "{{ problem_statement }}-{{ extra_key }}-{{ traj }}"
    comparison_template = "{{ thought1 }}||{{ action1 }}##{{ thought2 }}||{{ action2 }}"

    inst = make_instance(system_template, instance_template, comparison_template, formatted_traj="FORMATTED_TRAJ")

    ps = DummyProblemStatement("MY_PS", extra={"extra_key": "EXTRA"})

    msgs = inst.format_messages(
        problem_statement=ps,
        trajectory=[{"dummy": "step"}],
        thought1="T1",
        action1="A1",
        thought2="T2",
        action2="A2",
        use_cache_control=False,
    )

    # Expect three messages
    assert isinstance(msgs, list) and len(msgs) == 3

    # System message
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == system_template

    # Instance/user message (second element)
    assert msgs[1]["role"] == "user"
    # content is a list with a single dict
    assert isinstance(msgs[1]["content"], list) and len(msgs[1]["content"]) == 1
    inst_content = msgs[1]["content"][0]
    assert inst_content["type"] == "text"
    # No cache_control key when use_cache_control is False
    assert "cache_control" not in inst_content
    # Rendered text should combine problem statement, extra field, and formatted trajectory
    assert inst_content["text"] == "MY_PS-EXTRA-FORMATTED_TRAJ"

    # Comparison message (third element)
    assert msgs[2]["role"] == "user"
    comp_content_list = msgs[2]["content"]
    assert isinstance(comp_content_list, list) and len(comp_content_list) == 1
    comp = comp_content_list[0]
    assert comp["type"] == "text"
    assert comp["text"] == "T1||A1##T2||A2"

    # Ensure logger recorded the debug messages (at least the system and instance messages)
    # The logger messages should contain the system message and instance message content we set
    logged = "\n".join(inst._logger.messages)
    assert "SYSTEM_MSG" in logged
    assert "MY_PS-EXTRA-FORMATTED_TRAJ" in logged or "FORMATTED_TRAJ" in logged


def test_format_messages_with_cache_control():
    system_template = "SYS2"
    instance_template = "{{ problem_statement }}+{{ another }}+{{ traj }}"
    comparison_template = "{{ thought1 }}<>{{ action1 }}<>{{ thought2 }}<>{{ action2 }}"

    inst = make_instance(system_template, instance_template, comparison_template, formatted_traj="T_TRAJ")

    ps = DummyProblemStatement("PS2", extra={"another": "VAL"})

    msgs = inst.format_messages(
        problem_statement=ps,
        trajectory=[],
        thought1="THOUGHT1",
        action1="ACT1",
        thought2="THOUGHT2",
        action2="ACT2",
        use_cache_control=True,
    )

    assert isinstance(msgs, list) and len(msgs) == 3

    # Check system message unchanged
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "SYS2"

    # Check cache_control present in instance content
    inst_content = msgs[1]["content"][0]
    assert inst_content["type"] == "text"
    assert inst_content["text"] == "PS2+VAL+T_TRAJ"
    assert "cache_control" in inst_content
    assert inst_content["cache_control"] == {"type": "ephemeral"}

    # Comparison message unaffected by cache_control flag
    comp = msgs[2]["content"][0]
    assert comp["text"] == "THOUGHT1<>ACT1<>THOUGHT2<>ACT2"
    assert "cache_control" not in comp
