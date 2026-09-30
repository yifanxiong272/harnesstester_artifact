# file: sweagent/tools/tools.py:257-266
# asked: {"lines": [264, 265, 266], "branches": []}
# gained: {"lines": [264, 265, 266], "branches": []}

import asyncio
import pytest

from sweagent.tools.tools import ToolHandler


class DummyRuntime:
    def __init__(self, behavior):
        # behavior can be a normal return value or an Exception instance to raise
        self.behavior = behavior
        self.called = False
        self.last_cmd = None

    async def execute(self, cmd):
        self.called = True
        self.last_cmd = cmd
        if isinstance(self.behavior, Exception):
            raise self.behavior
        return self.behavior


class DummyDeployment:
    def __init__(self, runtime):
        self.runtime = runtime


class DummyEnv:
    def __init__(self, runtime):
        self.deployment = DummyDeployment(runtime)


class MinimalCommand:
    def __init__(self, name, end_name=None):
        self.name = name
        self.end_name = end_name


class ToolConfig:
    def __init__(self, commands=None, submit_command="submit", submit_command_end_name="end"):
        self.commands = commands or []
        self.submit_command = submit_command
        self.submit_command_end_name = submit_command_end_name

    def model_copy(self, deep=True):
        # Return self is fine for tests; ToolHandler uses the returned object's attributes only.
        return self


def make_handler_with_commands(names):
    cmds = [MinimalCommand(name=n) for n in names]
    cfg = ToolConfig(commands=cmds, submit_command="submit", submit_command_end_name="end")
    return ToolHandler(cfg)


def test_bash_skips_check_and_does_not_call_execute():
    """When command is 'bash', the method should return immediately and not call runtime.execute."""
    runtime = DummyRuntime(behavior="should not be used")
    env = DummyEnv(runtime)
    handler = make_handler_with_commands([])

    # Run the coroutine; it should return without calling runtime.execute
    asyncio.run(handler._is_command_available(env, "bash", {}))

    assert runtime.called is False, "runtime.execute must not be called for 'bash' command"


def test_command_available_calls_execute_and_returns_without_error():
    """When the runtime.execute completes successfully, no exception should be raised and execute is called."""
    runtime = DummyRuntime(behavior="ok")
    env = DummyEnv(runtime)
    handler = make_handler_with_commands(["ls"])

    # Should not raise
    asyncio.run(handler._is_command_available(env, "ls", {"PATH": "/usr/bin"}))

    assert runtime.called is True, "runtime.execute should have been called for non-'bash' command"
    assert runtime.last_cmd is not None, "runtime.execute should have been passed a command object"
    # The RexCommand passed in by ToolHandler should have a 'command' attribute like "which ls"
    assert getattr(runtime.last_cmd, "command", None) == "which ls"


def test_tool_not_available_raises_runtimeerror():
    """If runtime.execute raises an exception, _is_command_available should raise RuntimeError with expected message."""
    runtime = DummyRuntime(behavior=Exception("no such tool"))
    env = DummyEnv(runtime)
    handler = make_handler_with_commands(["nonexistent-tool"])

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(handler._is_command_available(env, "nonexistent-tool", {}))

    assert str(excinfo.value) == "Tool nonexistent-tool is not available in the container."
    assert runtime.called is True, "runtime.execute should have been called and then failed"
    # Ensure the attempted command was 'which nonexistent-tool'
    assert getattr(runtime.last_cmd, "command", None) == "which nonexistent-tool"
