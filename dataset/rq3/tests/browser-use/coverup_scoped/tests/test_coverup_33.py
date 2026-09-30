# file: browser_use/agent/service.py:1079-1152
# asked: {"lines": [1083, 1085, 1087, 1088, 1089, 1090, 1092, 1093, 1095, 1098, 1100, 1101, 1104, 1105, 1108, 1111, 1114, 1115, 1116, 1119, 1121, 1122, 1123, 1124, 1125, 1126, 1129, 1131, 1132, 1133, 1134, 1135, 1136, 1137, 1138, 1139, 1140, 1141, 1142, 1145, 1146, 1147, 1148, 1149, 1150, 1151, 1152], "branches": [[1092, 1093], [1092, 1095], [1115, 1116], [1115, 1119]]}
# gained: {"lines": [1083, 1085, 1087, 1088, 1089, 1090, 1092, 1093, 1095, 1098, 1100, 1101, 1104, 1105, 1108, 1111, 1114, 1115, 1116, 1119, 1121, 1122, 1123, 1124, 1125, 1126, 1129, 1131, 1132, 1133, 1134, 1135, 1136, 1137, 1138, 1139, 1140, 1141, 1142, 1145, 1146, 1147, 1148, 1149, 1150, 1151, 1152], "branches": [[1092, 1093], [1092, 1095], [1115, 1116], [1115, 1119]]}

import asyncio
import types
import pytest

from browser_use.agent.service import Agent
from types import SimpleNamespace

@pytest.mark.asyncio
async def test_prepare_context_with_screenshot_and_no_skills():
    calls = []

    class DummyLogger:
        def debug(self, msg):
            calls.append(("debug", msg))

    # browser session that returns a summary with a screenshot
    class DummyBrowserSession:
        async def get_browser_state_summary(self, include_screenshot=True, include_recent_events=False):
            return SimpleNamespace(url="http://example.com", screenshot=b"imagedata")

    # tools.registry.get_prompt_description returning empty list to test Falsey branch
    class DummyRegistry:
        def get_prompt_description(self, url):
            calls.append(("get_prompt_description", url))
            return []

    class DummyTools:
        def __init__(self):
            self.registry = DummyRegistry()

    # message manager that records calls and checks parameters
    class DummyMessageManager:
        def __init__(self):
            self.prepared = None
            self.created = None

        def prepare_step_state(self, **kwargs):
            self.prepared = kwargs
            calls.append(("prepare_step_state", kwargs))

        def create_state_messages(self, **kwargs):
            self.created = kwargs
            calls.append(("create_state_messages", kwargs))

    # Build a dummy self object to pass to Agent._prepare_context
    class DummySelf:
        browser_session = DummyBrowserSession()
        logger = DummyLogger()
        include_recent_events = False
        tools = DummyTools()
        skill_service = None  # ensure _get_unavailable_skills_info NOT called
        sensitive_data = {"foo": "bar"}
        available_file_paths = ["file1"]
        settings = SimpleNamespace(use_vision=True)
        state = SimpleNamespace(n_steps=1, last_model_output=None, last_result=None)
        _message_manager = DummyMessageManager()

        # async methods expected to be awaited by _prepare_context
        async def _check_and_update_downloads(self, ctx):
            calls.append(("_check_and_update_downloads", ctx))
            return None

        def _log_step_context(self, browser_state_summary):
            calls.append(("_log_step_context", browser_state_summary.url))

        async def _check_stop_or_pause(self):
            calls.append(("_check_stop_or_pause", True))

        async def _update_action_models_for_page(self, url):
            calls.append(("_update_action_models_for_page", url))

        async def _maybe_compact_messages(self, step_info):
            calls.append(("_maybe_compact_messages", step_info))

        def _render_plan_description(self):
            calls.append(("_render_plan_description", True))
            return None  # test branch where plan_description is None

        async def _inject_budget_warning(self, step_info):
            calls.append(("_inject_budget_warning", step_info))

        def _inject_replan_nudge(self):
            calls.append(("_inject_replan_nudge", True))

        def _inject_exploration_nudge(self):
            calls.append(("_inject_exploration_nudge", True))

        def _update_loop_detector_page_state(self, browser_state_summary):
            calls.append(("_update_loop_detector_page_state", browser_state_summary.url))

        def _inject_loop_detection_nudge(self):
            calls.append(("_inject_loop_detection_nudge", True))

        async def _force_done_after_last_step(self, step_info):
            calls.append(("_force_done_after_last_step", step_info))

        async def _force_done_after_failure(self):
            calls.append(("_force_done_after_failure", True))

    dummy = DummySelf()
    # Call Agent._prepare_context with dummy self
    result = await Agent._prepare_context(dummy, step_info=None)

    # Assertions: returned browser state is the object from DummyBrowserSession
    assert hasattr(result, "url") and result.url == "http://example.com"
    assert result.screenshot == b"imagedata"

    # Verify that key internal methods were called (order-independent)
    expected_called = {
        "_check_and_update_downloads",
        "_log_step_context",
        "_check_stop_or_pause",
        "_update_action_models_for_page",
        "get_prompt_description",
        "prepare_step_state",
        "_maybe_compact_messages",
        "create_state_messages",
        "_inject_budget_warning",
        "_inject_replan_nudge",
        "_inject_exploration_nudge",
        "_update_loop_detector_page_state",
        "_inject_loop_detection_nudge",
        "_force_done_after_last_step",
        "_force_done_after_failure",
    }
    called_names = set(name for name, _ in calls)
    assert expected_called.issubset(called_names)


@pytest.mark.asyncio
async def test_prepare_context_without_screenshot_and_with_skills_and_page_actions():
    calls = []

    class DummyLogger:
        def debug(self, msg):
            calls.append(("debug", msg))

    # browser session that returns a summary without a screenshot
    class DummyBrowserSession:
        async def get_browser_state_summary(self, include_screenshot=True, include_recent_events=False):
            return SimpleNamespace(url="http://another.example", screenshot=None)

    class DummyRegistry:
        def get_prompt_description(self, url):
            calls.append(("get_prompt_description", url))
            return ["action1", "action2"]

    class DummyTools:
        def __init__(self):
            self.registry = DummyRegistry()

    class DummyMessageManager:
        def __init__(self):
            self.prepared = None
            self.created = None

        def prepare_step_state(self, **kwargs):
            self.prepared = kwargs
            calls.append(("prepare_step_state", kwargs))

        def create_state_messages(self, **kwargs):
            self.created = kwargs
            calls.append(("create_state_messages", kwargs))

    class DummySelf:
        browser_session = DummyBrowserSession()
        logger = DummyLogger()
        include_recent_events = True
        tools = DummyTools()
        skill_service = object()  # non-None to force _get_unavailable_skills_info call
        sensitive_data = None
        available_file_paths = []
        settings = SimpleNamespace(use_vision=False)
        state = SimpleNamespace(n_steps=2, last_model_output={"x": 1}, last_result=[{"r": 1}])
        _message_manager = DummyMessageManager()

        async def _check_and_update_downloads(self, ctx):
            calls.append(("_check_and_update_downloads", ctx))

        def _log_step_context(self, browser_state_summary):
            calls.append(("_log_step_context", browser_state_summary.url))

        async def _check_stop_or_pause(self):
            calls.append(("_check_stop_or_pause", True))

        async def _update_action_models_for_page(self, url):
            calls.append(("_update_action_models_for_page", url))

        async def _get_unavailable_skills_info(self):
            calls.append(("_get_unavailable_skills_info", True))
            return "unavailable-skills"

        def _render_plan_description(self):
            calls.append(("_render_plan_description", True))
            return "PLAN"

        async def _maybe_compact_messages(self, step_info):
            calls.append(("_maybe_compact_messages", step_info))

        async def _inject_budget_warning(self, step_info):
            calls.append(("_inject_budget_warning", step_info))

        def _inject_replan_nudge(self):
            calls.append(("_inject_replan_nudge", True))

        def _inject_exploration_nudge(self):
            calls.append(("_inject_exploration_nudge", True))

        def _update_loop_detector_page_state(self, browser_state_summary):
            calls.append(("_update_loop_detector_page_state", browser_state_summary.url))

        def _inject_loop_detection_nudge(self):
            calls.append(("_inject_loop_detection_nudge", True))

        async def _force_done_after_last_step(self, step_info):
            calls.append(("_force_done_after_last_step", step_info))

        async def _force_done_after_failure(self):
            calls.append(("_force_done_after_failure", True))

    dummy = DummySelf()
    step_info = SimpleNamespace(info="step2")
    result = await Agent._prepare_context(dummy, step_info=step_info)

    # Verify return value
    assert hasattr(result, "url") and result.url == "http://another.example"
    assert result.screenshot is None

    # Ensure unavailable skills info was requested and plan_description inserted
    called_names = set(name for name, _ in calls)
    assert "_get_unavailable_skills_info" in called_names
    assert "_render_plan_description" in called_names

    # Validate that create_state_messages received page_filtered_actions as non-None
    created_calls = [args for name, args in calls if name == "create_state_messages"]
    # There should be at least one create_state_messages call and it should include page_filtered_actions
    assert created_calls, "create_state_messages was not called"
    created_kwargs = created_calls[0]
    # created_kwargs is the kwargs dict appended in the calls list
    assert isinstance(created_kwargs, dict) or isinstance(created_kwargs, tuple) or isinstance(created_kwargs, list)
    # The pattern we appended is ("create_state_messages", kwargs)
    if isinstance(created_kwargs, dict):
        kwargs = created_kwargs
    else:
        # It's actually stored as ("create_state_messages", kwargs)
        # find the kwargs by iterating calls to match the name
        for name, kw in calls:
            if name == "create_state_messages":
                kwargs = kw
                break
    # page_filtered_actions should be present and not None
    assert kwargs.get("page_filtered_actions") == ["action1", "action2"]
