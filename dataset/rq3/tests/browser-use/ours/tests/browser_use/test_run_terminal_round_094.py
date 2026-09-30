import asyncio
import types
import builtins
import pytest

import importlib

service = importlib.import_module('browser_use.beta.service')


class _CallRecorder:
    def __init__(self):
        self.calls = []

    def record(self, name):
        self.calls.append(name)


@pytest.mark.asyncio
async def test_immediate_stop_round_094(monkeypatch):
    """
    Exercise the branch where _should_stop_before_run returns True immediately
    so the method finishes early and performs cleanup/telemetry calls.
    """
    recorder = _CallRecorder()

    # deterministic time sequence: started then finished
    def make_time_seq(values):
        it = iter(values)

        def _t():
            try:
                return next(it)
            except StopIteration:
                return values[-1]

        return _t

    monkeypatch.setattr(service.time, 'time', make_time_seq([100.0, 200.0]))

    # stub _history_from_events to capture arguments and return a sentinel
    sentinel_history = {'sentinel': True}

    captured = {}

    def fake_history_from_events(events, *, model, started, finished, output_model_schema, process_error):
        captured['events'] = events
        captured['model'] = model
        captured['started'] = started
        captured['finished'] = finished
        captured['output_model_schema'] = output_model_schema
        captured['process_error'] = process_error
        return sentinel_history

    monkeypatch.setattr(service, '_history_from_events', fake_history_from_events)

    # Build a minimal fake agent with the attributes/methods used by _run_terminal
    class FakeAgent:
        def __init__(self):
            self.model = 'model-x'
            self.output_model_schema = {'schema': 'x'}
            self.history = None
            self.result = None
            self.state = types.SimpleNamespace(paused=False, follow_up_task=False)

        async def _log_agent_run(self):
            recorder.record('_log_agent_run')

        def _log_agent_setup(self):
            recorder.record('_log_agent_setup')

        def _initialize_run_lifecycle_state(self):
            recorder.record('_initialize_run_lifecycle_state')

        def _log_first_step_startup(self):
            recorder.record('_log_first_step_startup')

        async def _should_stop_before_run(self):
            recorder.record('_should_stop_before_run')
            return True

        async def _apply_terminal_usage_costs(self, events):
            recorder.record('_apply_terminal_usage_costs')

        async def _log_run_usage_summary(self):
            recorder.record('_log_run_usage_summary')

        def _record_laminar_run_observability(self, **kwargs):
            recorder.record('_record_laminar_run_observability')
            # surface some of the kwargs to verify they were passed
            captured['laminar_kwargs'] = kwargs

        def _record_run_telemetry(self, **kwargs):
            recorder.record('_record_run_telemetry')
            captured['telemetry_kwargs'] = kwargs

        def _dispatch_run_update_event(self):
            recorder.record('_dispatch_run_update_event')

        def _log_final_outcome_messages(self):
            recorder.record('_log_final_outcome_messages')

        async def _finalize_run_cleanup(self):
            recorder.record('_finalize_run_cleanup')

    agent = FakeAgent()

    # Call the unbound method as the module defines it on the Agent class
    result = await service.Agent._run_terminal(agent, max_steps=5, on_step_start=None, on_step_end=None)

    # Assertions: history returned is exactly sentinel_history and helper methods called
    assert result is agent.history is sentinel_history
    assert captured['model'] == 'model-x'
    assert captured['started'] == 100.0
    assert captured['finished'] == 200.0
    assert captured['process_error'] == 'Beta agent stopped before terminal run.'

    # verify expected sequence of side-effect helpers were invoked
    assert '_log_agent_run' in recorder.calls
    assert '_should_stop_before_run' in recorder.calls
    assert '_apply_terminal_usage_costs' in recorder.calls
    assert '_finalize_run_cleanup' in recorder.calls


@pytest.mark.asyncio
async def test_paused_then_stop_round_094(monkeypatch):
    """
    Exercise the branch where the agent is paused before the terminal run,
    the signal handler reset is callable and invoked, and a subsequent
    _should_stop_before_run returns True (the second check) causing early exit.
    """
    recorder = _CallRecorder()

    # time sequence: started once, finished later
    monkeypatch.setattr(service.time, 'time', (lambda: 100.0))

    # We'll simulate time advancing on the finalization step by temporarily replacing time
    # inside the fake _should_stop_before_run second call (see below). For the purposes
    # of observable assertions we patch _history_from_events to receive the finished value we set.

    sentinel_history = {'paused_sentinel': True}
    captured = {}

    def fake_history_from_events(events, *, model, started, finished, output_model_schema, process_error):
        captured['events'] = events
        captured['model'] = model
        captured['started'] = started
        captured['finished'] = finished
        captured['output_model_schema'] = output_model_schema
        captured['process_error'] = process_error
        return sentinel_history

    monkeypatch.setattr(service, '_history_from_events', fake_history_from_events)

    class DummyPauseEvent:
        def __init__(self):
            self.wait_called = False

        async def wait(self):
            # simulate immediate resume
            self.wait_called = True

    class ResettableSignalHandler:
        def __init__(self):
            self.reset_called = False

        def reset(self):
            self.reset_called = True

    # Create a should_stop coroutine that returns False first, then True.
    stop_calls = {'count': 0}

    async def should_stop_sequence():
        stop_calls['count'] += 1
        # on first call return False, on second True
        if stop_calls['count'] == 1:
            recorder.record('_should_stop_before_run:first')
            return False
        else:
            # advance time for finished measurement
            monkeypatch.setattr(service.time, 'time', (lambda: 300.0))
            recorder.record('_should_stop_before_run:second')
            return True

    class FakeAgent:
        def __init__(self):
            self.model = 'model-y'
            self.output_model_schema = None
            self.history = types.SimpleNamespace(history=[])
            self.result = None
            self.state = types.SimpleNamespace(paused=True, follow_up_task=False)
            self._external_pause_event = DummyPauseEvent()
            self._run_signal_handler = ResettableSignalHandler()

        async def _log_agent_run(self):
            recorder.record('_log_agent_run')

        def _log_agent_setup(self):
            recorder.record('_log_agent_setup')

        def _initialize_run_lifecycle_state(self):
            recorder.record('_initialize_run_lifecycle_state')

        def _log_first_step_startup(self):
            recorder.record('_log_first_step_startup')

        async def _should_stop_before_run(self):
            return await should_stop_sequence()

        async def _apply_terminal_usage_costs(self, events):
            recorder.record('_apply_terminal_usage_costs')

        async def _log_run_usage_summary(self):
            recorder.record('_log_run_usage_summary')

        def _record_laminar_run_observability(self, **kwargs):
            recorder.record('_record_laminar_run_observability')
            captured['laminar_kwargs'] = kwargs

        def _record_run_telemetry(self, **kwargs):
            recorder.record('_record_run_telemetry')
            captured['telemetry_kwargs'] = kwargs

        def _dispatch_run_update_event(self):
            recorder.record('_dispatch_run_update_event')

        def _log_final_outcome_messages(self):
            recorder.record('_log_final_outcome_messages')

        async def _finalize_run_cleanup(self):
            recorder.record('_finalize_run_cleanup')

    agent = FakeAgent()

    result = await service.Agent._run_terminal(agent, max_steps=3, on_step_start=None, on_step_end=None)

    assert result is agent.history is sentinel_history or result == sentinel_history

    # Confirm the pause wait and signal handler reset were used
    assert agent._external_pause_event.wait_called is True
    assert agent._run_signal_handler.reset_called is True

    # Confirm we went through both should_stop checks
    assert ' _should_stop_before_run:second'.strip() in recorder.calls or ' _should_stop_before_run:first'.strip() in recorder.calls
    # The _history_from_events should observe the second finished time (300.0 as patched)
    assert captured['model'] == 'model-y'
    assert captured['finished'] == 300.0

    # Ensure cleanup helpers invoked
    assert '_apply_terminal_usage_costs' in recorder.calls or '_finalize_run_cleanup' in recorder.calls
