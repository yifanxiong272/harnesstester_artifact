import pytest
from aider.commands import Commands

class DummyIO:
    def __init__(self):
        self.last = None

    def tool_output(self, val):
        self.last = val


def make_self(coder_test_cmd=None, cmd_run_func=None):
    """Create a minimal fake 'self' with the attributes Commands.cmd_test expects.

    - coder.test_cmd: used when args is falsy
    - io.tool_output: to capture tool output calls
    - cmd_run: used when args is a str
    """
    s = type("S", (), {})()
    s.coder = type("C", (), {"test_cmd": coder_test_cmd})()
    s.io = DummyIO()
    # cmd_run should be callable with signature (args, add_on_nonzero_exit)
    if cmd_run_func is None:
        s.cmd_run = lambda args, add_on_nonzero_exit: "ran:" + args
    else:
        s.cmd_run = cmd_run_func
    return s


def test_cmd_test_uses_coder_test_cmd_round_128():
    # When args is falsy but coder.test_cmd is set, cmd_test should use coder.test_cmd
    s = make_self(coder_test_cmd="doit")
    res = Commands.cmd_test(s, args=None)
    assert res == "ran:doit"
    # No tool_output should have been invoked for the cmd_run path
    assert s.io.last is None


def test_cmd_test_returns_none_when_no_args_and_no_coder_test_cmd_round_128():
    # When args falsy and coder.test_cmd falsy -> early return None
    s = make_self(coder_test_cmd=None)
    res = Commands.cmd_test(s, args=None)
    assert res is None
    assert s.io.last is None


def test_cmd_test_raises_for_non_str_non_callable_round_128():
    # When args is neither callable nor str, should raise ValueError(repr(args))
    s = make_self()
    with pytest.raises(ValueError) as exc:
        Commands.cmd_test(s, args=123)
    # repr(123) -> '123' so the message should contain 123
    assert "123" in str(exc.value)


def test_cmd_test_callable_returns_falsy_round_128():
    # When args is callable and returns falsy, cmd_test should return None and not call tool_output
    s = make_self()
    def f():
        return None
    res = Commands.cmd_test(s, args=f)
    assert res is None
    assert s.io.last is None


def test_cmd_test_callable_returns_errors_calls_tool_output_round_128():
    # When args is callable and returns errors (truthy), cmd_test should call io.tool_output and return errors
    s = make_self()
    def f():
        return "error!"
    res = Commands.cmd_test(s, args=f)
    assert res == "error!"
    assert s.io.last == "error!"
