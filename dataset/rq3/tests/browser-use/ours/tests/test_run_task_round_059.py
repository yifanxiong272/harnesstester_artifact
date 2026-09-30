import asyncio
import logging
from unittest.mock import Mock, patch

import pytest

import importlib

# Import the module under test
import browser_use.cli as cli


def _make_app_instance():
    """Create a minimal BrowserUseApp instance without calling its real __init__.
    We'll set only the attributes needed by run_task.
    """
    AppCls = cli.BrowserUseApp
    app = AppCls.__new__(AppCls)
    # defaults used across tests
    app.config = {}
    app.llm = None
    app.agent = None
    app.controller = None
    app.browser_session = None
    app._telemetry = Mock()
    app.hide_intro_panels = Mock()
    app.setup_event_bus_listener = Mock()
    app.call_after_refresh = Mock()
    app.scroll_to_input = Mock()
    # Provide a query_one that can be customized by tests via attribute
    app._query_mapping = {}

    def query_one(selector, *args, **kwargs):
        # Return mapping value or raise to surfacing bugs
        if selector in app._query_mapping:
            return app._query_mapping[selector]
        raise KeyError(f"No mock for selector: {selector}")

    app.query_one = query_one
    return app


def test_run_task_raises_when_llm_not_initialized_round_059():
    app = _make_app_instance()

    # AgentSettings.model_validate should be called; provide a stub return
    class DummySettings:
        def model_dump(self):
            return {"dummy": True}

    with patch.object(cli, "AgentSettings", autospec=True) as mock_settings_cls:
        # model_validate used as classmethod in the code; emulate it returning DummySettings
        mock_settings_cls.model_validate = staticmethod(lambda cfg: DummySettings())

        # Provide a rich log for main output with clear tracking
        rich_log = Mock()
        app._query_mapping["#main-output-log"] = rich_log

        # Call run_task and assert the expected RuntimeError when llm is None
        with pytest.raises(RuntimeError) as excinfo:
            app.run_task("do-something")

        assert "LLM not initialized" in str(excinfo.value)
        # hide_intro_panels and rich_log.clear are called before the LLM check
        app.hide_intro_panels.assert_called_once()
        rich_log.clear.assert_called_once()


def test_run_task_add_new_task_when_agent_present_round_059():
    app = _make_app_instance()

    # Provide required AgentSettings.model_validate to avoid unrelated failures
    with patch.object(cli, "AgentSettings", autospec=True) as mock_settings_cls:
        mock_settings_cls.model_validate = staticmethod(lambda cfg: Mock(model_dump=lambda: {}))

        # Simulate an existing agent with add_new_task
        agent_mock = Mock()
        app.agent = agent_mock

        # Provide minimal rich log mapping
        rich_log = Mock()
        app._query_mapping["#main-output-log"] = rich_log

        # Replace run_worker so we do NOT execute the background worker in this test,
        # but we capture that run_worker was invoked with a coroutine function
        recorded = {}

        def fake_run_worker(fn, name=None):
            # record that run_worker was called and that fn is callable (async def)
            recorded["called"] = True
            recorded["fn_callable"] = callable(fn)
            recorded["name"] = name

        app.run_worker = fake_run_worker

        # Execute
        app.run_task("task-123")

        # The existing agent should receive add_new_task
        agent_mock.add_new_task.assert_called_once_with("task-123")
        # run_worker should have been invoked with a coroutine function and name
        assert recorded.get("called") is True
        assert recorded.get("fn_callable") is True
        assert recorded.get("name") == "agent_task"


def test_run_task_creates_agent_and_runs_round_059():
    app = _make_app_instance()

    # Prepare Dummy Agent class to patch into the module so constructor is exercised
    class DummyAgent:
        def __init__(self, task, llm, controller, browser_session, source, **kwargs):
            # store constructor args for inspection
            self._ctor = dict(task=task, llm=llm, controller=controller, browser_session=browser_session, source=source, extras=kwargs)
            # ensure a browser_session attribute exists to exercise the hasattr branch
            self.browser_session = "agent_browser_session"
            self.running = False
            self.last_response_time = None
            self.run_called = False

        async def run(self):
            # Simulate some async work
            self.run_called = True

    # Dummy Controller used when app.controller is falsy
    class DummyController:
        pass

    # Dummy settings object returned by AgentSettings.model_validate
    class DummySettings:
        def model_dump(self):
            return {"setting_a": "value_a"}

    # Patch Agent, Controller, and AgentSettings in the cli module
    with patch.object(cli, "Agent", new=DummyAgent), patch.object(cli, "Controller", new=DummyController), patch.object(cli, "AgentSettings", autospec=True) as mock_settings_cls:
        mock_settings_cls.model_validate = staticmethod(lambda cfg: DummySettings())

        # Provide a mock LLM with model and provider attributes to exercise telemetry fields
        llm_obj = Mock()
        llm_obj.model = "test-model"
        llm_obj.provider = "test-provider"
        app.llm = llm_obj

        # Ensure controller is falsy so Controller() path is taken
        app.controller = None

        # Provide mapping for required query selectors
        rich_log = Mock()
        task_input_container = type("Container", (), {"display": False})()
        input_field = Mock()
        app._query_mapping["#main-output-log"] = rich_log
        app._query_mapping["#task-input-container"] = task_input_container
        app._query_mapping["#task-input"] = input_field

        # Replace call_after_refresh to verify it is called with scroll_to_input
        call_after = Mock()
        app.call_after_refresh = call_after

        captured_telemetry = []

        def capture_telemetry(evt):
            # Append the telemetry event object so tests can inspect its attributes
            captured_telemetry.append(evt)

        app._telemetry = Mock()
        app._telemetry.capture = capture_telemetry

        # Implement run_worker to synchronously execute the passed async function
        def real_run_worker(fn, name=None):
            # fn is the async function (not yet awaited). Run it to completion.
            # Use asyncio.run to execute the coroutine returned by calling fn().
            # This keeps the behavior deterministic within pytest.
            asyncio.run(fn())

        app.run_worker = real_run_worker

        # Execute the method under test; should construct DummyAgent and run the worker
        app.run_task("do-real-work")

        # After execution, telemetry should have been captured twice: message_sent and task_completed
        assert len(captured_telemetry) >= 2
        actions = [getattr(evt, "action", None) for evt in captured_telemetry]
        assert "message_sent" in actions
        assert "task_completed" in actions

        # The agent attribute should now reference the DummyAgent instance
        assert isinstance(app.agent, DummyAgent)

        # The app.browser_session should have been updated from the agent
        assert app.browser_session == "agent_browser_session"

        # The agent should have been run and then have running reset to False
        assert app.agent.run_called is True
        assert app.agent.running is False

        # The UI elements should have been adjusted
        assert task_input_container.display is True
        input_field.focus.assert_called_once()
        call_after.assert_called_once_with(app.scroll_to_input)
