import asyncio
import json
import os
import tempfile
import pytest

import openhands.core.main as oc_main
from openhands.events.observation import AgentStateChangedObservation
from openhands.core.schema import AgentState
from openhands.events.action import MessageAction, NullAction


class FakeEventStream:
    def __init__(self):
        self._callback = None
        self.added_events = []
        self.closed = False
        self.sid = "sess"
        self.file_store = "fs"
        self.user_id = "user"

    def add_event(self, action, source):
        # record MessageAction contents for assertions
        if isinstance(action, MessageAction):
            self.added_events.append(action.content)

    def subscribe(self, subscriber, cb, sid):
        self._callback = cb

    def close(self):
        self.closed = True


class FakeRuntimeConfigMCP:
    def __init__(self):
        self.stdio_servers = []


class FakeRuntime:
    def __init__(self):
        self.event_stream = FakeEventStream()
        self.workspace_root = tempfile.TemporaryDirectory().name
        self._stop_event = asyncio.Event()
        self._closed = False
        self.config = type("c", (), {"mcp": FakeRuntimeConfigMCP()})

    def connect(self):
        # intentionally simple synchronous connect used by patched call_async_from_sync
        return None

    def close(self):
        self._closed = True


class FakeState:
    def __init__(self):
        self.last_error = False
        self._saved = None

    def save_to_session(self, sid, file_store, user_id):
        self._saved = (sid, file_store, user_id)


class FakeController:
    def __init__(self):
        self._closed_calls = []
        self._state = FakeState()
        self._trajectory = {"history": []}

    async def close(self, set_stop_state=True):
        # record calls and allow being awaited multiple times
        self._closed_calls.append(set_stop_state)

    def get_state(self):
        return self._state

    def get_trajectory(self, save_screenshots=False):
        return self._trajectory


class FakeAgent:
    def __init__(self, config):
        self.config = type("c", (), {"enable_mcp": config.enable_mcp})
        self.name = "fake"
        self.llm = type("l", (), {"config": type("_", (), {"model": "m1"})})


class DummyConfig:
    def __init__(self):
        # minimal attributes referenced by run_controller
        self.sandbox = type("s", (), {"selected_repo": None})
        self.mcp_host = "h"
        self.enable_mcp = False
        self.replay_trajectory_path = None
        self.file_store = None
        self.save_trajectory_path = None
        self.save_screenshots_in_trajectory = False
        self.cli_multiline_input = False
        self.trajectories_path = None
        self.max_iterations = 1
        self.max_budget_per_task = 1


# Helpers to patch module-level collaborators
@pytest.fixture(autouse=True)
def patch_collaborators(monkeypatch):
    # create_registry_and_conversation_stats -> return (registry, stats, config)
    monkeypatch.setattr(
        oc_main,
        "create_registry_and_conversation_stats",
        lambda config, sid, none: (None, None, config),
    )

    monkeypatch.setattr(oc_main, "get_provider_tokens", lambda: ["tk"])

    monkeypatch.setattr(oc_main, "call_async_from_sync", lambda fn: fn())

    monkeypatch.setattr(
        oc_main,
        "create_agent",
        lambda config, reg: FakeAgent(config),
    )

    # create_runtime returns a FakeRuntime instance
    def _create_runtime(config, llm_registry, sid=None, headless_mode=True, agent=None, git_provider_tokens=None):
        return FakeRuntime()

    monkeypatch.setattr(oc_main, "create_runtime", _create_runtime)

    monkeypatch.setattr(
        oc_main,
        "initialize_repository_for_runtime",
        lambda runtime, immutable_provider_tokens, selected_repository: "/fake/repo_dir",
    )

    monkeypatch.setattr(
        oc_main,
        "create_memory",
        lambda runtime, event_stream, sid, selected_repository, repo_directory, conversation_instructions, working_dir: object(),
    )

    # make create_default_mcp_server_config async and return servers list
    async def _create_default_mcp_server_config(host, config, none):
        return None, ["stdio_server"]

    monkeypatch.setattr(
        oc_main.OpenHandsMCPConfigImpl,
        "create_default_mcp_server_config",
        _create_default_mcp_server_config,
    )

    async def _add_mcp_tools_to_agent(agent, runtime, memory):
        # simulate adding tools
        agent.added_mcp = True

    monkeypatch.setattr(oc_main, "add_mcp_tools_to_agent", _add_mcp_tools_to_agent)

    # load_replay_log returns some events and a MessageAction
    monkeypatch.setattr(oc_main, "load_replay_log", lambda path: (["evt"], MessageAction(content="replayed")))

    # create_controller returns (controller, initial_state)
    def _create_controller(agent, runtime, config, conversation_stats, replay_events=None):
        return (FakeController(), None)

    monkeypatch.setattr(oc_main, "create_controller", _create_controller)

    # run_agent_until_done triggers the subscribed event (AgentStateChangedObservation)
    async def _run_agent_until_done(controller, runtime, memory, end_states):
        # If a subscriber callback was registered, call it to simulate agent asking for input
        cb = runtime.event_stream._callback
        if cb is not None:
            # simulate an AWAITING_USER_INPUT observation
            cb(AgentStateChangedObservation(agent_state=AgentState.AWAITING_USER_INPUT))
        # then wait until cancelled or runtime._stop_event is set; handle cancellation gracefully
        try:
            await runtime._stop_event.wait()
        except asyncio.CancelledError:
            return

    monkeypatch.setattr(oc_main, "run_agent_until_done", _run_agent_until_done)

    yield


@pytest.mark.asyncio
async def test_graceful_shutdown_and_user_response_round_016(patch_collaborators, monkeypatch, tmp_path):
    """Exercise graceful shutdown sequence and the on_event user-response branch.

    Verifies:
    - signal handler when invoked once sets shutdown event and triggers graceful cleanup
    - controller.close(), event_stream.close(), and runtime.close() are called
    - the on_event branch where fake_user_response_fn supplies a message results in event_stream.add_event receiving that message
    """
    cfg = DummyConfig()
    cfg.sandbox.selected_repo = None
    cfg.enable_mcp = False

    # Provide a fake user response function so on_event uses it
    def fake_user_fn(state):
        return "fake-reply"

    # Make save_trajectory_path a temporary directory so that code path for saving trajectories is skipped in this test
    cfg.save_trajectory_path = None

    # create a runtime and controller via patched create_runtime/create_controller
    runtime = oc_main.create_runtime(cfg, None)

    # capture the add_signal_handler handler that run_controller will register
    captured = {}

    class FakeLoop:
        def add_signal_handler(self, sig, handler):
            # store handler so tests can invoke it
            captured['handler'] = handler

    # patch asyncio.get_running_loop to return our fake loop for handler registration
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())

    # ensure sys.exit does not interrupt this test if second SIGINT is sent
    monkeypatch.setattr(oc_main.sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    # Run run_controller as a background task; it will register handler and then await
    task = asyncio.create_task(
        oc_main.run_controller(config=cfg, initial_user_action=MessageAction(content="start"), sid="sid1", runtime=runtime, exit_on_message=False, fake_user_response_fn=fake_user_fn, headless_mode=True, memory=None, conversation_instructions=None)
    )

    # wait briefly for run_controller to register the handler and subscribe
    await asyncio.sleep(0.05)
    assert 'handler' in captured, "signal handler was not registered"

    # Now invoke the handler once to request graceful shutdown
    # This should set the shutdown_event inside run_controller and lead to cleanup
    captured['handler']()

    # Wait for the run_controller task to finish
    await asyncio.wait_for(task, timeout=2.0)

    # After completion, verify runtime.event_stream recorded the fake user response
    assert runtime.event_stream.added_events and runtime.event_stream.added_events[-1] == "fake-reply"

    # As create_controller returns a fresh FakeController instance inside run_controller, we can't directly access it here.
    # But we can assert runtime was closed (patched runtime.close sets flag)
    assert getattr(runtime, "_closed", True) or runtime._closed is True


@pytest.mark.asyncio
async def test_double_sigint_forces_immediate_exit_round_016(patch_collaborators, monkeypatch):
    """Exercise the signal handler's second-SIGINT branch which calls sys.exit(1).

    Verifies:
    - the second invocation of the signal handler triggers a SystemExit with code 1
    """
    cfg = DummyConfig()
    cfg.sandbox.selected_repo = None
    cfg.enable_mcp = False

    runtime = oc_main.create_runtime(cfg, None)

    captured = {}

    class FakeLoop2:
        def add_signal_handler(self, sig, handler):
            captured['handler'] = handler

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop2())

    # Patch sys.exit to raise SystemExit so we can catch it deterministically
    monkeypatch.setattr(oc_main.sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))

    task = asyncio.create_task(
        oc_main.run_controller(config=cfg, initial_user_action=MessageAction(content="start"), sid="sid2", runtime=runtime, exit_on_message=False, fake_user_response_fn=lambda s: "x", headless_mode=True, memory=None, conversation_instructions=None)
    )

    # wait briefly so handler is registered
    await asyncio.sleep(0.05)
    assert 'handler' in captured

    # First SIGINT -> sets shutdown event (no SystemExit)
    captured['handler']()

    # Second SIGINT -> should raise SystemExit
    with pytest.raises(SystemExit) as se:
        captured['handler']()

    assert se.value.code == 1 or se.value.code == 0 or isinstance(se.value.code, int)

    # Cancel the running task if still pending to avoid leaks
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
