# file: browser_use/beta/service.py:5041-5129
# asked: {"lines": [5053, 5054, 5055, 5056, 5057, 5058, 5059, 5060, 5062, 5063, 5064, 5065, 5066, 5067, 5068, 5070, 5071, 5072, 5073, 5074, 5076, 5077, 5078, 5079, 5080, 5081, 5082, 5083, 5084, 5085, 5086, 5087, 5088, 5089, 5090, 5092, 5093, 5094, 5095, 5096, 5097, 5098, 5100, 5101, 5102, 5103, 5104], "branches": [[5052, 5053], [5075, 5076], [5080, 5081], [5080, 5082], [5082, 5083], [5082, 5106], [5114, 5121]]}
# gained: {"lines": [5053, 5054, 5055, 5056, 5057, 5058, 5059, 5060, 5062, 5063, 5064, 5065, 5066, 5067, 5068, 5070, 5071, 5072, 5073, 5074, 5076, 5077, 5078, 5079, 5080, 5081, 5082, 5083, 5084, 5085, 5086, 5087, 5088, 5089, 5090, 5092, 5093, 5094, 5095, 5096, 5097, 5098, 5100, 5101, 5102, 5103, 5104], "branches": [[5052, 5053], [5075, 5076], [5080, 5081], [5082, 5083]]}

import asyncio
import types
import pytest

import browser_use.beta.service as service
from browser_use.beta.service import Agent


class DummyLogger:
    def __init__(self):
        self.debug_messages = []

    def debug(self, msg):
        self.debug_messages.append(msg)


class DummyHistory:
    def __init__(self, initial=None):
        self.history = list(initial or [])


class DummyEvent:
    def __init__(self, set_immediately=True):
        self._set = set_immediately

    async def wait(self):
        if self._set:
            return
        await asyncio.sleep(0.001)


@pytest.mark.asyncio
async def test_run_terminal_stops_before_run(monkeypatch):
    # Ensure Agent.logger property returns a DummyLogger instance so tests can call .debug if needed.
    monkeypatch.setattr(service.Agent, "logger", property(lambda self: DummyLogger()), raising=False)

    ag = object.__new__(Agent)

    # set up state and attributes used by _run_terminal
    ag.model = "m"
    ag.output_model_schema = "schema"
    ag.state = types.SimpleNamespace(paused=False, follow_up_task=False)
    ag._external_pause_event = DummyEvent()
    ag._sdk_agent_id = None
    ag.task = {"name": "original"}
    ag._completed_initial_navigation_urls = ["u1"]
    ag.initial_action_payloads = ["p1"]
    ag._completed_initial_navigation_states = ["s1"]

    # history object
    ag.history = DummyHistory()
    ag.result = None

    # Track calls to various methods
    called = {}

    async def _log_agent_run():
        called["_log_agent_run"] = True

    def _log_agent_setup():
        called["_log_agent_setup"] = True

    def _initialize_run_lifecycle_state():
        called["_initialize_run_lifecycle_state"] = True

    def _log_first_step_startup():
        called["_log_first_step_startup"] = True

    # First check should stop -> True
    async def _should_stop_before_run():
        called["_should_stop_before_run_calls"] = called.get("_should_stop_before_run_calls", 0) + 1
        return True

    async def _apply_terminal_usage_costs(arg):
        called["_apply_terminal_usage_costs"] = arg

    async def _log_run_usage_summary():
        called["_log_run_usage_summary"] = True

    def _record_laminar_run_observability(**kwargs):
        called["_record_laminar_run_observability"] = kwargs

    def _record_run_telemetry(**kwargs):
        called["_record_run_telemetry"] = kwargs

    def _dispatch_run_update_event():
        called["_dispatch_run_update_event"] = True

    def _log_final_outcome_messages():
        called["_log_final_outcome_messages"] = True

    async def _finalize_run_cleanup():
        called["_finalize_run_cleanup"] = True

    # assign methods
    ag._log_agent_run = _log_agent_run
    ag._log_agent_setup = _log_agent_setup
    ag._initialize_run_lifecycle_state = _initialize_run_lifecycle_state
    ag._log_first_step_startup = _log_first_step_startup
    ag._should_stop_before_run = _should_stop_before_run
    ag._apply_terminal_usage_costs = _apply_terminal_usage_costs
    ag._log_run_usage_summary = _log_run_usage_summary
    ag._record_laminar_run_observability = _record_laminar_run_observability
    ag._record_run_telemetry = _record_run_telemetry
    ag._dispatch_run_update_event = _dispatch_run_update_event
    ag._log_final_outcome_messages = _log_final_outcome_messages
    ag._finalize_run_cleanup = _finalize_run_cleanup

    # call _run_terminal
    res = await service.Agent._run_terminal(ag, max_steps=5, on_step_start=None, on_step_end=None)

    # Assertions: stopped before run so history should equal result and cleanup called
    assert res is ag.history
    assert called.get("_log_agent_run") is True
    assert called.get("_apply_terminal_usage_costs") == []
    assert called.get("_log_run_usage_summary") is True
    assert called.get("_record_laminar_run_observability") is not None
    assert called.get("_record_run_telemetry") is not None
    assert called.get("_dispatch_run_update_event") is True
    assert called.get("_log_final_outcome_messages") is True
    assert called.get("_finalize_run_cleanup") is True
    # ensure _should_stop_before_run was checked at least once
    assert called.get("_should_stop_before_run_calls", 0) >= 1


@pytest.mark.asyncio
async def test_run_terminal_paused_then_stops(monkeypatch):
    monkeypatch.setattr(service.Agent, "logger", property(lambda self: DummyLogger()), raising=False)

    ag = object.__new__(Agent)

    ag.model = "m"
    ag.output_model_schema = "schema"
    # state paused True to enter paused branch
    ag.state = types.SimpleNamespace(paused=True, follow_up_task=False)
    ag._external_pause_event = DummyEvent(set_immediately=True)
    ag._sdk_agent_id = None
    ag.task = {"name": "original"}
    ag._completed_initial_navigation_urls = []
    ag.initial_action_payloads = []
    ag._completed_initial_navigation_states = []
    ag.history = DummyHistory()
    ag.result = None

    called = {}

    async def _log_agent_run():
        called["_log_agent_run"] = True

    def _log_agent_setup():
        called["_log_agent_setup"] = True

    def _initialize_run_lifecycle_state():
        called["_initialize_run_lifecycle_state"] = True

    def _log_first_step_startup():
        called["_log_first_step_startup"] = True

    # should_stop_before_run returns False the first time (so not stopping at initial check),
    # then True after pause wait to trigger stopped branch in paused block.
    responses = [False, True]

    async def _should_stop_before_run():
        called["_should_stop_before_run_calls"] = called.get("_should_stop_before_run_calls", 0) + 1
        return responses.pop(0)

    # provide a signal handler with reset() to be called
    reset_called = {"val": False}

    class SigHandler:
        def reset(self):
            reset_called["val"] = True

    ag._run_signal_handler = SigHandler()

    async def _apply_terminal_usage_costs(arg):
        called["_apply_terminal_usage_costs"] = arg

    async def _log_run_usage_summary():
        called["_log_run_usage_summary"] = True

    def _record_laminar_run_observability(**kwargs):
        called["_record_laminar_run_observability"] = kwargs

    def _record_run_telemetry(**kwargs):
        called["_record_run_telemetry"] = kwargs

    def _dispatch_run_update_event():
        called["_dispatch_run_update_event"] = True

    def _log_final_outcome_messages():
        called["_log_final_outcome_messages"] = True

    async def _finalize_run_cleanup():
        called["_finalize_run_cleanup"] = True

    ag._log_agent_run = _log_agent_run
    ag._log_agent_setup = _log_agent_setup
    ag._initialize_run_lifecycle_state = _initialize_run_lifecycle_state
    ag._log_first_step_startup = _log_first_step_startup
    ag._should_stop_before_run = _should_stop_before_run
    ag._apply_terminal_usage_costs = _apply_terminal_usage_costs
    ag._log_run_usage_summary = _log_run_usage_summary
    ag._record_laminar_run_observability = _record_laminar_run_observability
    ag._record_run_telemetry = _record_run_telemetry
    ag._dispatch_run_update_event = _dispatch_run_update_event
    ag._log_final_outcome_messages = _log_final_outcome_messages
    ag._finalize_run_cleanup = _finalize_run_cleanup

    # call _run_terminal
    res = await service.Agent._run_terminal(ag, max_steps=3, on_step_start=None, on_step_end=None)

    # Assertions: ensure paused branch executed and reset was called
    assert res is ag.history
    assert reset_called["val"] is True
    assert called.get("_apply_terminal_usage_costs") == []
    assert called.get("_finalize_run_cleanup") is True
    # verify should_stop_before_run called twice (initial + after resume)
    assert called.get("_should_stop_before_run_calls", 0) >= 2


@pytest.mark.asyncio
async def test_run_terminal_calls_task_context_and_runs_sdk_agent(monkeypatch):
    monkeypatch.setattr(service.Agent, "logger", property(lambda self: DummyLogger()), raising=False)

    ag = object.__new__(Agent)

    ag.model = "m"
    ag.output_model_schema = "schema"
    # make follow_up_task True but _sdk_agent_id falsy to ensure followup False branch is reached
    ag.state = types.SimpleNamespace(paused=False, follow_up_task=True)
    ag._sdk_agent_id = None
    ag.task = {"name": "original"}
    ag._completed_initial_navigation_urls = ["url1"]
    ag.initial_action_payloads = ["payload1"]
    ag._completed_initial_navigation_states = ["state1"]
    ag.history = DummyHistory()
    ag._pending_history_prefix = None
    ag.result = None

    called = {}

    async def _log_agent_run():
        called["_log_agent_run"] = True

    def _log_agent_setup():
        called["_log_agent_setup"] = True

    def _initialize_run_lifecycle_state():
        called["_initialize_run_lifecycle_state"] = True

    def _log_first_step_startup():
        called["_log_first_step_startup"] = True

    async def _should_stop_before_run():
        called["_should_stop_before_run_calls"] = called.get("_should_stop_before_run_calls", 0) + 1
        return False

    async def _execute_initial_actions(allow_terminal_run=False):
        # do not change history to keep pending prefix logic minimal
        called["_execute_initial_actions"] = allow_terminal_run

    async def _call_callback(cb, arg):
        called["_call_callback"] = (cb, arg)

    def _log_main_execution_start(max_steps):
        called["_log_main_execution_start"] = max_steps

    # monkeypatch the module-level helper to observe its call
    recorded_task_context = {}

    def fake_task_with_completed_initial_navigation_context(task, urls, payloads, states):
        recorded_task_context["task"] = task.copy() if isinstance(task, dict) else task
        recorded_task_context["urls"] = list(urls)
        recorded_task_context["payloads"] = list(payloads)
        recorded_task_context["states"] = list(states)
        # return a modified task to signal it was called
        new = dict(task) if isinstance(task, dict) else {"wrapped": task}
        new["wrapped"] = True
        return new

    monkeypatch.setattr(
        service,
        "_task_with_completed_initial_navigation_context",
        fake_task_with_completed_initial_navigation_context,
        raising=False,
    )

    # fake _run_sdk_agent should be awaited and return a sentinel
    sdk_called = {}

    async def _run_sdk_agent(task, max_steps, started, on_step_end, source, followups):
        sdk_called["task"] = task
        sdk_called["max_steps"] = max_steps
        sdk_called["source"] = source
        sdk_called["followups"] = followups
        return "SDK_RESULT"

    ag._log_agent_run = _log_agent_run
    ag._log_agent_setup = _log_agent_setup
    ag._initialize_run_lifecycle_state = _initialize_run_lifecycle_state
    ag._log_first_step_startup = _log_first_step_startup
    ag._should_stop_before_run = _should_stop_before_run
    ag._execute_initial_actions = _execute_initial_actions
    ag._call_callback = _call_callback
    ag._log_main_execution_start = _log_main_execution_start
    ag._run_sdk_agent = _run_sdk_agent

    # Execute
    res = await service.Agent._run_terminal(ag, max_steps=7, on_step_start=None, on_step_end=None)

    # Assertions
    assert res == "SDK_RESULT"
    # ensure helper was called and provided correct args
    assert recorded_task_context["task"] == {"name": "original"}
    assert recorded_task_context["urls"] == ["url1"]
    assert recorded_task_context["payloads"] == ["payload1"]
    assert recorded_task_context["states"] == ["state1"]
    # ensure _run_sdk_agent received the transformed task (with "wrapped": True)
    assert sdk_called["task"].get("wrapped") is True
    assert sdk_called["max_steps"] == 7
    assert sdk_called["source"] == "run"
    # ensure initial actions and callbacks were invoked
    assert called["_execute_initial_actions"] is False
    assert called["_log_main_execution_start"] == 7
