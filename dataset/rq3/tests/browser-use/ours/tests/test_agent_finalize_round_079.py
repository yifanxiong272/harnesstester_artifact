import asyncio
import types
import time
import pytest

import browser_use.agent.service as service_mod

pytest_plugins = []

# All test functions must end with _round_079

class DummyEventBus:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class DummyHistoryItem:
    def __init__(self, metadata=None):
        self.metadata = metadata


class DummyMetadata:
    def __init__(self, start, end):
        self.step_start_time = start
        self.step_end_time = end


class DummyActionWithDump:
    def model_dump(self):
        return {"dumped": True}


class DummyActionWithoutDump:
    pass


@pytest.mark.asyncio
async def test_finalize_returns_when_no_last_result_round_079():
    # Arrange: create minimal fake self with last_result falsy
    dummy = types.SimpleNamespace()
    dummy.state = types.SimpleNamespace()
    dummy.state.last_result = None
    dummy.state.last_model_output = None
    dummy.state.n_steps = 5
    dummy.history = types.SimpleNamespace()
    dummy.history.history = []
    dummy.step_start_time = 123.0
    # Methods that should NOT be called
    called = {"save_fs": False}

    def save_fs():
        called["save_fs"] = True

    dummy.save_file_system_state = save_fs
    dummy._make_history_item = None
    dummy._message_manager = types.SimpleNamespace(last_state_message_text=None)
    dummy._log_step_completion_summary = lambda *_: None
    dummy._demo_mode_log = None
    dummy.eventbus = DummyEventBus()

    # Act
    await service_mod.Agent._finalize(dummy, None)

    # Assert: early return happened, save_file_system_state not called, n_steps unchanged
    assert called["save_fs"] is False
    assert dummy.state.n_steps == 5


@pytest.mark.asyncio
async def test_finalize_without_browser_summary_triggers_demo_log_round_079():
    # Arrange: last_result present but no browser summary
    dummy = types.SimpleNamespace()
    dummy.state = types.SimpleNamespace()
    dummy.state.last_result = {"ok": True}
    dummy.state.last_model_output = None
    dummy.state.n_steps = 0
    dummy.history = types.SimpleNamespace()
    dummy.history.history = []
    dummy.step_start_time = 1.23
    # Capture calls
    demo_called = {"called": False, "args": None}

    async def demo_log(message, level, metadata):
        demo_called["called"] = True
        demo_called["args"] = (message, level, metadata)

    def save_fs():
        demo_called.setdefault("save_fs_called", True)

    dummy._make_history_item = None
    dummy._message_manager = types.SimpleNamespace(last_state_message_text="STATE")
    dummy._log_step_completion_summary = lambda step_start_time, result: "SOME SUMMARY"
    dummy._demo_mode_log = demo_log
    dummy.save_file_system_state = save_fs
    dummy.eventbus = DummyEventBus()

    # Act
    await service_mod.Agent._finalize(dummy, None)

    # Assert: demo log awaited and n_steps incremented
    assert demo_called["called"] is True
    assert demo_called["args"][1] == "info"
    assert demo_called["args"][2] == {"step": 0}
    assert dummy.state.n_steps == 1


@pytest.mark.asyncio
async def test_finalize_with_browser_summary_and_empty_history_round_079():
    # Arrange: browser_state_summary provided, empty history -> metadata.step_interval should be None
    dummy = types.SimpleNamespace()
    dummy.state = types.SimpleNamespace()
    dummy.state.last_result = {"ok": True}
    dummy.state.last_model_output = None
    dummy.state.n_steps = 2
    dummy.history = types.SimpleNamespace()
    dummy.history.history = []
    dummy.step_start_time = 100.0
    made = {"called": False, "args": None}

    async def fake_make_history_item(model_output, browser_state_summary, last_result, metadata, state_message=None):
        made["called"] = True
        made["args"] = (model_output, browser_state_summary, last_result, metadata, state_message)

    dummy._make_history_item = fake_make_history_item
    dummy._message_manager = types.SimpleNamespace(last_state_message_text="X")
    dummy._log_step_completion_summary = lambda s, r: None
    dummy._demo_mode_log = lambda *a, **k: None
    saved = {"called": False}

    def save_fs():
        saved["called"] = True

    dummy.save_file_system_state = save_fs
    dummy.eventbus = DummyEventBus()

    browser_summary = object()

    # Act
    await service_mod.Agent._finalize(dummy, browser_summary)

    # Assert: _make_history_item called and metadata.step_interval is None
    assert made["called"] is True
    _, _, _, metadata_obj, state_message = made["args"]
    # metadata_obj is StepMetadata instance from module
    assert isinstance(metadata_obj, service_mod.StepMetadata)
    assert metadata_obj.step_interval is None
    assert state_message == "X"
    assert saved["called"] is True
    assert dummy.state.n_steps == 3


@pytest.mark.asyncio
async def test_finalize_with_actions_and_event_dispatch_round_079():
    # Arrange: provide browser_state_summary, history with previous metadata, and last_model_output with actions
    dummy = types.SimpleNamespace()
    dummy.state = types.SimpleNamespace()
    dummy.state.last_result = {"ok": True}
    # last_model_output needs an 'action' attribute for the actions loop
    last_model_output = types.SimpleNamespace()
    last_model_output.action = [DummyActionWithDump(), DummyActionWithoutDump()]
    dummy.state.last_model_output = last_model_output
    dummy.state.n_steps = 7
    # History has one item with metadata
    prev_meta = DummyMetadata(start=10.0, end=13.5)
    dummy.history = types.SimpleNamespace()
    dummy.history.history = [DummyHistoryItem(metadata=prev_meta)]
    dummy.step_start_time = 50.0

    made = {"called": False}

    async def fake_make_history_item(model_output, browser_state_summary, last_result, metadata, state_message=None):
        made["called"] = True
        made["metadata"] = metadata

    dummy._make_history_item = fake_make_history_item
    dummy._message_manager = types.SimpleNamespace(last_state_message_text=None)
    # Force no demo message
    dummy._log_step_completion_summary = lambda s, r: None
    dummy._demo_mode_log = lambda *a, **k: None
    saved = {"called": False}

    def save_fs():
        saved["called"] = True

    dummy.save_file_system_state = save_fs
    bus = DummyEventBus()
    dummy.eventbus = bus

    # Patch CreateAgentStepEvent.from_agent_step in module to capture the actions_data passed
    captured = {"args": None}

    def fake_from_agent_step(agent_self, model_output, result, actions_data, browser_state_summary):
        captured["args"] = (agent_self, model_output, result, actions_data, browser_state_summary)
        return {"event": "sentinel"}

    orig_creator = service_mod.CreateAgentStepEvent.from_agent_step
    service_mod.CreateAgentStepEvent.from_agent_step = fake_from_agent_step

    browser_summary = object()

    try:
        # Act
        await service_mod.Agent._finalize(dummy, browser_summary)

        # Assert: history maker called, step_interval computed as previous_end - previous_start
        assert made["called"] is True
        metadata_obj = made["metadata"]
        assert isinstance(metadata_obj, service_mod.StepMetadata)
        assert metadata_obj.step_interval == pytest.approx(3.5)
        # Assert that CreateAgentStepEvent.from_agent_step was given actions data where first action is dict and second is {}
        assert captured["args"] is not None
        _agent_self, model_output_arg, result_arg, actions_data_arg, browser_summary_arg = captured["args"]
        assert model_output_arg is last_model_output
        assert result_arg == dummy.state.last_result
        assert isinstance(actions_data_arg, list)
        assert actions_data_arg[0] == {"dumped": True}
        assert actions_data_arg[1] == {}
        # Event was dispatched
        assert bus.dispatched == [{"event": "sentinel"}]
        assert saved["called"] is True
        assert dummy.state.n_steps == 8
    finally:
        # restore
        service_mod.CreateAgentStepEvent.from_agent_step = orig_creator
