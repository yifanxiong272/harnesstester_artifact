import pytest

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class _DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        # store debug messages for later inspection
        self.messages.append(str(msg))


class _DummyProblemStatement:
    def __init__(self, statement="PROB", extra=None):
        self._statement = statement
        self._extra = {} if extra is None else extra

    def get_problem_statement(self):
        return self._statement

    def get_extra_fields(self):
        return dict(self._extra)


class _ConfigStub:
    def __init__(self, system_template, instance_template, comparison_template):
        self.system_template = system_template
        self.instance_template = instance_template
        self.comparison_template = comparison_template


def _make_comparator_with_stubs(system_tmpl, instance_tmpl, comparison_tmpl, traj_render="TRAJSTR"):
    # Create instance without invoking __init__ to avoid side effects
    comp = BinaryTrajectoryComparison.__new__(BinaryTrajectoryComparison)
    comp.config = _ConfigStub(system_tmpl, instance_tmpl, comparison_tmpl)
    comp._logger = _DummyLogger()
    # Patch _format_trajectory to return a deterministic representation
    comp._format_trajectory = lambda traj: traj_render
    return comp


def test_format_messages_without_cache_control_round_051():
    # Templates intentionally use the provided rendering variables
    system_tmpl = "SYSTEM-OK"
    instance_tmpl = "PS={{problem_statement}};X={{extra}};T={{traj}}"
    comparison_tmpl = "TH1={{thought1}}|A1={{action1}} -- TH2={{thought2}}|A2={{action2}}"

    comp = _make_comparator_with_stubs(system_tmpl, instance_tmpl, comparison_tmpl, traj_render="TRAJ_VAL")

    ps = _DummyProblemStatement(statement="THE_PROB", extra={"extra": "EXTRA_VAL"})

    out = comp.format_messages(
        problem_statement=ps,
        trajectory=[],  # any value is fine; _format_trajectory is patched
        thought1="thinkA",
        action1="actA",
        thought2="thinkB",
        action2="actB",
        use_cache_control=False,
    )

    # Expect three messages: system, user (instance), user (comparison)
    assert isinstance(out, list) and len(out) == 3

    # 1) system message preserved verbatim from config.system_template
    assert out[0]["role"] == "system"
    assert out[0]["content"] == system_tmpl

    # 2) user instance piece: content is a list containing a dict with text and no cache_control
    assert out[1]["role"] == "user"
    user_contents = out[1]["content"]
    assert isinstance(user_contents, list) and len(user_contents) == 1
    user_item = user_contents[0]
    assert user_item["type"] == "text"
    # Template rendering should have substituted problem_statement, extra, and traj
    assert user_item["text"] == "PS=THE_PROB;X=EXTRA_VAL;T=TRAJ_VAL"
    # No cache_control when use_cache_control is False
    assert "cache_control" not in user_item

    # 3) comparison message is rendered from the comparison template
    assert out[2]["role"] == "user"
    comp_contents = out[2]["content"]
    assert comp_contents and comp_contents[0]["text"] == "TH1=thinkA|A1=actA -- TH2=thinkB|A2=actB"

    # Ensure debug logging happened for system, instance, and comparison inputs
    # The dummy logger should have captured three debug calls
    dbg = comp._logger.messages
    assert any("MODEL INPUT (system)" in m or "SYSTEM-OK" in m for m in dbg)
    assert any("MODEL INPUT (instance)" in m or "PS=THE_PROB" in m for m in dbg)
    assert any("MODEL INPUT (comparison)" in m or "TH1=thinkA" in m for m in dbg)


def test_format_messages_with_cache_control_round_051():
    # Same templates but test that cache_control is injected when requested
    system_tmpl = "SYST"
    instance_tmpl = "P={{problem_statement}}|E={{extra}}|R={{traj}}"
    comparison_tmpl = "C1={{thought1}};C2={{thought2}}"

    comp = _make_comparator_with_stubs(system_tmpl, instance_tmpl, comparison_tmpl, traj_render="ZTR")

    ps = _DummyProblemStatement(statement="PST", extra={"extra": "EVAL"})

    out = comp.format_messages(
        problem_statement=ps,
        trajectory=None,
        thought1="t1",
        action1="a1",
        thought2="t2",
        action2="a2",
        use_cache_control=True,
    )

    # Inspect the user instance content for cache_control presence
    user_item = out[1]["content"][0]
    assert user_item["text"] == "P=PST|E=EVAL|R=ZTR"
    assert "cache_control" in user_item
    assert user_item["cache_control"] == {"type": "ephemeral"}

    # Also verify comparison message text
    assert out[2]["content"][0]["text"] == "C1=t1;C2=t2"

    # Verify system message too
    assert out[0]["content"] == system_tmpl
