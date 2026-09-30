import types
from jinja2 import Template
from sweagent.agent.reviewer import Reviewer


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.info_calls = []

    def debug(self, msg):
        # record debug messages for assertions
        self.debug_calls.append(msg)

    def info(self, msg):
        self.info_calls.append(msg)

    def warning(self, msg, exc_info=False):
        # keep shape compatible with real logger
        pass


class DummyTrajFormatter:
    def __init__(self, out="<TRAJ>"):
        self.out = out
        self.called_with = None

    def format_trajectory(self, trajectory):
        # record call and return deterministic string
        self.called_with = trajectory
        return self.out


class DummyInstance:
    def __init__(self, problem_statement, extra_fields=None):
        self._ps = problem_statement
        self._extra = extra_fields or {}

    def get_problem_statement(self):
        return self._ps

    def get_extra_fields(self):
        return dict(self._extra)


class DummySubmission:
    def __init__(self, fmt_dict=None, trajectory=None):
        self._fmt = fmt_dict or {}
        self.trajectory = trajectory

    def to_format_dict(self, suffix: str | None = None):
        # matching signature used by format_messages (no suffix passed)
        return dict(self._fmt)


def make_reviewer_with_config(system_template, instance_template, traj_formatter_return):
    # Bypass __init__ to avoid needing ReviewerConfig/TrajectoryFormatter internals
    reviewer = Reviewer.__new__(Reviewer)
    cfg = types.SimpleNamespace()
    cfg.system_template = system_template
    cfg.instance_template = instance_template
    # other config fields not needed for format_messages
    reviewer._config = cfg
    reviewer.logger = DummyLogger()
    reviewer._traj_formatter = DummyTrajFormatter(out=traj_formatter_return)
    return reviewer


def test_format_messages_basic_round_069():
    # Prepare reviewer with simple templates
    system_t = "SYSTEM_MESSAGE"
    instance_t = "PS={{ problem_statement }}|EXTRA={{ extra }}|SUB={{ submission_field }}|TR={{ traj }}"
    reviewer = make_reviewer_with_config(system_t, instance_t, traj_formatter_return="T-STR")

    inst = DummyInstance("the problem", extra_fields={"extra": "E"})
    sub = DummySubmission(fmt_dict={"submission_field": "S"}, trajectory=[{"step": 1}])

    messages = reviewer.format_messages(inst, sub)

    # System message preserved
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == system_t

    # User message is rendered and contains all provided fields
    user_msg = messages[1]["content"]
    assert "the problem" in user_msg
    assert "E" in user_msg
    assert "S" in user_msg
    assert "T-STR" in user_msg

    # logger.debug should have been called for system and user inputs
    # ensure two debug records and that they contain expected substrings
    debug_msgs = reviewer.logger.debug_calls
    assert any("MODEL INPUT (system)" in d for d in debug_msgs)
    assert any("MODEL INPUT (user)" in d for d in debug_msgs)

    # Confirm the trajectory formatter was invoked with the submission trajectory
    assert reviewer._traj_formatter.called_with == sub.trajectory


def test_format_messages_ps_override_round_069():
    # If extra fields override 'problem_statement', the template should use override
    system_t = "S2"
    instance_t = "PS={{ problem_statement }}|EXTRA={{ extra }}|TR={{ traj }}"
    reviewer = make_reviewer_with_config(system_t, instance_t, traj_formatter_return="TRX")

    # extra_fields provides an overriding problem_statement key
    inst = DummyInstance("original ps", extra_fields={"problem_statement": "OVERRIDE", "extra": "E2"})
    sub = DummySubmission(fmt_dict={}, trajectory=None)

    messages = reviewer.format_messages(inst, sub)

    user_msg = messages[1]["content"]
    # The override should be present in the rendered output
    assert "OVERRIDE" in user_msg
    # original should not appear (ensures override took effect)
    assert "original ps" not in user_msg
    # trajectory formatter was called even with None trajectory
    assert reviewer._traj_formatter.called_with is None
