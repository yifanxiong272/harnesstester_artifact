# file: openhands/core/main.py:59-319
# asked: {"lines": [119, 120, 121, 122, 123, 124, 125, 126, 129, 132, 133, 134, 135, 136, 143, 144, 145, 146, 147, 148, 149, 150, 168, 169, 170, 171, 179, 193, 195, 196, 197, 198, 200, 201, 210, 211, 213, 226, 227, 228, 229, 231, 232, 233, 266, 269, 271, 272, 275, 276, 279, 280, 283, 284, 287, 289, 290, 292, 293, 310, 311, 313, 314, 315, 316, 317], "branches": [[117, 119], [132, 133], [132, 139], [142, 143], [167, 168], [195, 196], [195, 200], [208, 210], [225, 226], [226, 227], [226, 228], [228, 229], [228, 231], [265, 266], [296, 303], [308, 310], [310, 311], [310, 313]]}
# gained: {"lines": [119, 120, 121, 122, 123, 124, 125, 126, 129, 132, 133, 134, 135, 136, 143, 144, 145, 146, 147, 148, 149, 150, 168, 169, 170, 171, 193, 195, 196, 197, 198, 266, 269, 271, 272, 275, 276, 279, 280, 283, 284, 287, 310, 311, 313, 314, 315, 316, 317], "branches": [[117, 119], [132, 133], [132, 139], [142, 143], [167, 168], [195, 196], [265, 266], [296, 303], [308, 310], [310, 311], [310, 313]]}

import asyncio
import json
import os
import types
import tempfile
import pathlib
import pytest

import openhands.core.main as main_mod
from openhands.events.action import MessageAction, NullAction


@pytest.mark.asyncio
async def test_run_controller_shutdown_and_save_trajectory_dir(monkeypatch, tmp_path):
    """
    Test the branch where:
    - runtime is created (get_provider_tokens, create_runtime, initialize_repository_for_runtime)
    - memory is created
    - signal handler triggers shutdown_event (simulate SIGINT) so graceful cleanup runs
    - config.file_store path is set and end_state.save_to_session is called
    - save_trajectory_path is a directory so file gets saved as <sid>.json
    """
    called = {}

    # Minimal fake config
    class FakeSandbox:
        selected_repo = "repo/name"

    class FakeConfig:
        sandbox = FakeSandbox()
        mcp_host = "host"
        replay_trajectory_path = None
        file_store = "session-store"
        save_trajectory_path = str(tmp_path)  # directory branch
        save_screenshots_in_trajectory = False
        cli_multiline_input = False
        enable_mcp = False
        trajectories_path = None
        max_iterations = None
        max_budget_per_task = None
        jwt_secret = "secret"  # required by generate_sid

        def __repr__(self):
            return "<FakeConfig>"

    config = FakeConfig()

    # monkeypatch create_registry_and_conversation_stats
    def fake_create_registry_and_conversation_stats(cfg, sid, none):
        return {}, {}, cfg

    monkeypatch.setattr(main_mod, "create_registry_and_conversation_stats", fake_create_registry_and_conversation_stats)

    # create_agent returns an object with expected attributes
    class FakeLLMConfig:
        model = "model-x"

    class FakeLLM:
        config = FakeLLMConfig()

    class FakeAgentConfig:
        enable_mcp = False

    class FakeAgent:
        name = "agent-name"
        llm = FakeLLM()
        config = FakeAgentConfig()

    monkeypatch.setattr(main_mod, "create_agent", lambda cfg, reg: FakeAgent())

    # provider tokens and create_runtime
    monkeypatch.setattr(main_mod, "get_provider_tokens", lambda: {"token": "x"})

    class FakeEventStream:
        def __init__(self):
            self.subscribers = {}
            self.sid = "fake-sid"
            self.file_store = "fs"
            self.user_id = "user-1"

        def add_event(self, *args, **kwargs):
            called.setdefault("add_event", []).append((args, kwargs))

        def subscribe(self, name, callback, sid):
            # store the callback; not calling it now
            self.subscribers[name] = callback
            called["subscribed_with_sid"] = sid

        def close(self):
            called["eventstream_closed"] = True

    class FakeRuntimeConfig:
        mcp = types.SimpleNamespace(stdio_servers=[])

    class FakeRuntime:
        def __init__(self):
            self.event_stream = FakeEventStream()
            self.workspace_root = tmp_path
            self.config = FakeRuntimeConfig()
            self.closed = False

        async def connect(self):
            called["runtime_connected"] = True

        def close(self):
            self.closed = True
            called["runtime_closed"] = True

    monkeypatch.setattr(main_mod, "create_runtime", lambda cfg, reg, sid=None, headless_mode=None, agent=None, git_provider_tokens=None: FakeRuntime())

    # call_async_from_sync should schedule the coroutine to run in the current loop
    def fake_call_async_from_sync(coro):
        if asyncio.iscoroutinefunction(coro):
            asyncio.create_task(coro())
        elif asyncio.iscoroutine(coro):
            asyncio.create_task(coro)
        else:
            coro()
        called["call_async_from_sync"] = True

    monkeypatch.setattr(main_mod, "call_async_from_sync", fake_call_async_from_sync)

    # initialize_repository_for_runtime should be invoked
    def fake_initialize_repository_for_runtime(runtime, immutable_provider_tokens=None, selected_repository=None):
        called["initialized_repo"] = selected_repository
        return str(tmp_path / "repo_dir")

    monkeypatch.setattr(main_mod, "initialize_repository_for_runtime", fake_initialize_repository_for_runtime)

    # create_memory
    class FakeMemory:
        pass

    def fake_create_memory(runtime=None, event_stream=None, sid=None, selected_repository=None, repo_directory=None, conversation_instructions=None, working_dir=None):
        called["create_memory"] = (sid, selected_repository, repo_directory, working_dir)
        return FakeMemory()

    monkeypatch.setattr(main_mod, "create_memory", fake_create_memory)

    # create_controller returns controller and initial_state (without last_error)
    class FakeEndState:
        def __init__(self):
            self.saved = []

        def save_to_session(self, sid, file_store, user_id):
            self.saved.append((sid, file_store, user_id))
            called["saved_to_session"] = (sid, file_store, user_id)

    class FakeController:
        def __init__(self):
            self._state = FakeEndState()
            self.closed_calls = []

        def get_state(self):
            return self._state

        async def close(self, set_stop_state=True):
            self.closed_calls.append(set_stop_state)
            called.setdefault("controller_closed", []).append(set_stop_state)

        def get_trajectory(self, save_screenshots):
            return [{"traj": True, "screenshots": save_screenshots}]

    monkeypatch.setattr(main_mod, "create_controller", lambda agent, runtime, cfg, conv_stats, replay_events=None: (FakeController(), None))

    # run_agent_until_done - make this a coroutine that would sleep; shutdown is triggered via signal handler
    async def fake_run_agent_until_done(controller, runtime, memory, end_states):
        await asyncio.sleep(0.05)
        return "done"

    monkeypatch.setattr(main_mod, "run_agent_until_done", fake_run_agent_until_done)

    # monkeypatch get_running_loop.add_signal_handler to call handler immediately to set shutdown_event
    class FakeLoop:
        def add_signal_handler(self, signum, handler):
            # simulate SIGINT immediately so shutdown_event will be set
            handler()
            called["signal_handler_called"] = True

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())

    # other dependencies that might be referenced
    monkeypatch.setattr(main_mod, "add_mcp_tools_to_agent", lambda a, r, m: asyncio.sleep(0))

    # run the controller
    state = await main_mod.run_controller(config=config, initial_user_action=MessageAction(content="hi"))

    # Assertions: cleanup steps were invoked and file created
    assert called.get("initialized_repo") == "repo/name"
    assert "create_memory" in called
    # saved to session should have been called
    assert called.get("saved_to_session") == ("fake-sid", "fs", "user-1")
    # controller.close should have been called at least once (cleanup and final close)
    assert "controller_closed" in called and len(called["controller_closed"]) >= 1
    # trajectory file exists in directory branch
    files = list(tmp_path.glob("*.json"))
    assert files, f"No trajectory file written in directory branch under {tmp_path}"
    # validate content of the json file created
    p = files[0]
    with open(p, "r") as f:
        content = json.load(f)
    assert isinstance(content, list)
    assert content[0].get("traj") is True


@pytest.mark.asyncio
async def test_run_controller_replay_and_save_trajectory_file(monkeypatch, tmp_path):
    """
    Test:
    - replay_trajectory_path branch (requires initial_user_action NullAction and load_replay_log)
    - save_trajectory_path is a specific file path (non-directory) so the else branch used
    """
    called = {}

    class FakeSandbox:
        selected_repo = None

    class FakeConfig:
        sandbox = FakeSandbox()
        mcp_host = "host"
        replay_trajectory_path = "some/path"  # trigger replay logic
        file_store = None
        save_trajectory_path = str(tmp_path / "traj_output.json")  # file path branch
        save_screenshots_in_trajectory = True
        cli_multiline_input = True
        enable_mcp = False
        trajectories_path = None
        max_iterations = None
        max_budget_per_task = None
        jwt_secret = "secret2"

        def __repr__(self):
            return "<FakeConfig2>"

    config = FakeConfig()

    monkeypatch.setattr(main_mod, "create_registry_and_conversation_stats", lambda cfg, sid, none: ({}, {}, cfg))
    class FakeAgent:
        name = "agent"
        llm = types.SimpleNamespace(config=types.SimpleNamespace(model="m"))
        config = types.SimpleNamespace(enable_mcp=False)
    monkeypatch.setattr(main_mod, "create_agent", lambda cfg, reg: FakeAgent())
    monkeypatch.setattr(main_mod, "get_provider_tokens", lambda: {})
    class FakeEventStream:
        def __init__(self):
            self.subscribers = {}
            self.sid = "sid-2"
            self.file_store = "fs2"
            self.user_id = "user-42"

        def add_event(self, *args, **kwargs):
            called.setdefault("add_event", []).append((args, kwargs))

        def subscribe(self, name, callback, sid):
            self.subscribers[name] = callback
            # store for potential invocation by tests
            called.setdefault("stored_callback", []).append((callback, None))

        def close(self):
            called["eventstream_closed"] = True

    class FakeRuntime:
        def __init__(self):
            self.event_stream = FakeEventStream()
            self.workspace_root = tmp_path
            self.config = types.SimpleNamespace(mcp=types.SimpleNamespace(stdio_servers=[]))
        async def connect(self):
            called["runtime_connected"] = True
        def close(self):
            called["runtime_closed"] = True

    monkeypatch.setattr(main_mod, "create_runtime", lambda cfg, reg, sid=None, headless_mode=None, agent=None, git_provider_tokens=None: FakeRuntime())
    monkeypatch.setattr(main_mod, "call_async_from_sync", lambda coro: None)
    monkeypatch.setattr(main_mod, "initialize_repository_for_runtime", lambda runtime, immutable_provider_tokens=None, selected_repository=None: None)
    monkeypatch.setattr(main_mod, "create_memory", lambda **kwargs: object())

    # load_replay_log must return replay_events and a real Action instance (MessageAction)
    def fake_load_replay_log(path):
        called["replay_loaded"] = path
        return ([], MessageAction(content="from_replay"))
    monkeypatch.setattr(main_mod, "load_replay_log", fake_load_replay_log)

    # create_controller: provide controller and an initial_state with last_error False so initial_user_action is used
    class FakeController:
        def __init__(self):
            self._state = types.SimpleNamespace(last_error=False)
            self.closed_calls = []
        def get_state(self):
            return self._state
        async def close(self, set_stop_state=True):
            self.closed_calls.append(set_stop_state)
        def get_trajectory(self, save_screenshots):
            return [{"x": 1, "screenshots": save_screenshots}]

    monkeypatch.setattr(main_mod, "create_controller", lambda agent, runtime, cfg, conv_stats, replay_events=None: (FakeController(), types.SimpleNamespace(last_error=False)))

    # run_agent_until_done should finish quickly
    async def fake_run_agent_until_done(controller, runtime, memory, end_states):
        await asyncio.sleep(0.01)
        return "ok"

    monkeypatch.setattr(main_mod, "run_agent_until_done", fake_run_agent_until_done)

    # capture add_signal_handler but do not call handler
    class FakeLoop:
        def add_signal_handler(self, signum, handler):
            called["signal_registered"] = True

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: FakeLoop())

    # run with initial_user_action NullAction to satisfy replay branch
    state = await main_mod.run_controller(config=config, initial_user_action=NullAction())

    # Verify replay log loaded
    assert called.get("replay_loaded") == "some/path"

    # There should be a trajectory file at the specific path
    traj_path = pathlib.Path(config.save_trajectory_path)
    assert traj_path.exists()
    with open(traj_path, "r") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert data[0]["x"] == 1
    assert data[0]["screenshots"] is True
