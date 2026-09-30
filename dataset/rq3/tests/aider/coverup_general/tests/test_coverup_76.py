# file: aider/commands.py:983-1001
# asked: {"lines": [986, 989, 993, 996, 997, 998, 1000, 1001], "branches": [[985, 986], [988, 989], [991, 996], [992, 993], [997, 998], [997, 1000]]}
# gained: {"lines": [986, 989, 993, 996, 997, 998, 1000, 1001], "branches": [[985, 986], [988, 989], [991, 996], [992, 993], [997, 998], [997, 1000]]}

import pytest
from types import SimpleNamespace

from aider.commands import Commands


def make_instance():
    # Create a lightweight object to act as `self` for Commands.cmd_test
    inst = SimpleNamespace()
    inst.coder = SimpleNamespace(test_cmd=None)
    inst.io = SimpleNamespace()
    return inst


def test_cmd_test_returns_none_when_no_args_and_no_test_cmd():
    inst = make_instance()
    # ensure no cmd_run and no tool_output are present/called
    inst.cmd_run = lambda *a, **k: (_ for _ in ()).throw(AssertionError("cmd_run should not be called"))
    inst.io.tool_output = lambda *a, **k: (_ for _ in ()).throw(AssertionError("tool_output should not be called"))

    result = Commands.cmd_test(inst, None)
    assert result is None


def test_cmd_test_uses_coder_test_cmd_string_and_calls_cmd_run():
    inst = make_instance()
    inst.coder.test_cmd = "echo hi"

    called = {}
    def fake_cmd_run(arg, flag):
        called['arg'] = arg
        called['flag'] = flag
        return "cmd_run_result"

    # tool_output should not be called for string (non-callable) path
    inst.io.tool_output = lambda *a, **k: (_ for _ in ()).throw(AssertionError("tool_output should not be called"))
    inst.cmd_run = fake_cmd_run

    result = Commands.cmd_test(inst, None)  # no args provided -> uses coder.test_cmd
    assert result == "cmd_run_result"
    assert called == {'arg': "echo hi", 'flag': True}


def test_cmd_test_raises_on_non_str_non_callable_args():
    inst = make_instance()
    inst.coder.test_cmd = None

    with pytest.raises(ValueError) as exc:
        Commands.cmd_test(inst, 123)
    # ensure the error message includes the repr of the bad arg
    assert "123" in str(exc.value)


def test_cmd_test_callable_returns_no_errors_returns_none():
    inst = make_instance()
    inst.coder.test_cmd = None

    def no_errors():
        return ""  # falsy

    # tool_output should not be called
    inst.io.tool_output = lambda *a, **k: (_ for _ in ()).throw(AssertionError("tool_output should not be called"))
    # cmd_run shouldn't be used either
    inst.cmd_run = lambda *a, **k: (_ for _ in ()).throw(AssertionError("cmd_run should not be called"))

    result = Commands.cmd_test(inst, no_errors)
    assert result is None


def test_cmd_test_callable_returns_errors_calls_tool_output_and_returns_errors():
    inst = make_instance()
    inst.coder.test_cmd = None

    def errors_func():
        return "some error occurred"

    recorded = {}
    def fake_tool_output(value):
        recorded['value'] = value

    inst.io.tool_output = fake_tool_output
    inst.cmd_run = lambda *a, **k: (_ for _ in ()).throw(AssertionError("cmd_run should not be called"))

    result = Commands.cmd_test(inst, errors_func)
    assert result == "some error occurred"
    assert recorded.get('value') == "some error occurred"
