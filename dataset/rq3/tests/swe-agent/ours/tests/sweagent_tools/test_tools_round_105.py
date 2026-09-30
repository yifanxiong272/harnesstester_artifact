import asyncio
import pytest

from types import SimpleNamespace

import sweagent.tools.tools as tools_module

# We'll call the unbound async method directly to avoid needing a full ToolHandler instance.
_is_command_available = tools_module.ToolHandler._is_command_available


class DummyRuntime:
    def __init__(self, behavior):
        # behavior is an async callable that will be awaited when execute is called
        self._behavior = behavior

    async def execute(self, cmd):
        return await self._behavior(cmd)


class DummyDeployment:
    def __init__(self, runtime):
        self.runtime = runtime


class DummyEnv:
    def __init__(self, runtime_behavior):
        self.deployment = DummyDeployment(DummyRuntime(runtime_behavior))


def test_bash_short_circuits_round_105():
    """
    When command == 'bash', the method should return immediately and not call runtime.execute.
    """

    called = {"count": 0}

    async def behavior(cmd):
        called["count"] += 1
        return None

    env = DummyEnv(behavior)

    # Call the async function synchronously using asyncio.run
    asyncio.run(_is_command_available(None, env, "bash", {}))

    # Ensure execute was never called
    assert called["count"] == 0, "runtime.execute should not be called for 'bash'"


def test_execute_success_calls_runtime_with_which_command_round_105():
    """
    When runtime.execute completes successfully, the method should return and the
    RexCommand passed into runtime.execute should carry the expected 'which <command>' string.
    """

    captured = {"arg": None}

    async def behavior(cmd):
        # capture the argument and simulate successful execution
        captured["arg"] = cmd
        return None

    env = DummyEnv(behavior)

    command_name = "mytool"
    asyncio.run(_is_command_available(None, env, command_name, {"KEY": "VAL"}))

    # Ensure something was passed to runtime.execute
    assert captured["arg"] is not None, "runtime.execute was not called"

    # The code under test constructs a command like f"which {command_name}" and passes a RexCommand object.
    # We assert that the object has an attribute 'command' with the expected payload.
    cmd_obj = captured["arg"]
    cmd_value = getattr(cmd_obj, "command", None)
    assert cmd_value == f"which {command_name}", (
        "Expected the RexCommand.command to equal the 'which' invocation; got: {}".format(cmd_value)
    )

    # Also assert that if the object exposes 'shell' and 'check' attributes they are set truthily as expected.
    # If these attributes don't exist, getattr will return the default None and the assertion will skip.
    shell_val = getattr(cmd_obj, "shell", None)
    check_val = getattr(cmd_obj, "check", None)
    if shell_val is not None:
        assert shell_val is True
    if check_val is not None:
        assert check_val is True


def test_execute_failure_raises_runtime_error_round_105():
    """
    When runtime.execute raises any Exception, the method should raise a RuntimeError with
    the specific message: "Tool {command} is not available in the container." and suppress the original exception.
    """

    async def behavior(cmd):
        raise Exception("nope")

    env = DummyEnv(behavior)

    command_name = "missing-tool"

    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(_is_command_available(None, env, command_name, {}))

    assert str(excinfo.value) == f"Tool {command_name} is not available in the container.", (
        "RuntimeError message did not match expected user-facing message"
    )
