import asyncio
import types
import pytest

from browser_use.agent.service import Agent


class DummyLogger:
    def __init__(self):
        self.debug_messages = []

    def debug(self, msg):
        # store for assertions
        self.debug_messages.append(str(msg))


class DummyBrowserStateSummary:
    def __init__(self, url, screenshot):
        self.url = url
        self.screenshot = screenshot


class DummyRegistry:
    def __init__(self, response):
        self._response = response

    def get_prompt_description(self, url):
        # mirror the real API shape: may return falsy or truthy
        return self._response


class DummyTools:
    def __init__(self, prompt_response):
        self.registry = DummyRegistry(prompt_response)


# Patch Agent.logger property at class level so instances created via object.__new__ will
# have a working logger without trying to set the read-only property on the instance.
Agent.logger = property(lambda self: DummyLogger())


@pytest.mark.asyncio
async def test_prepare_context_with_screenshot_no_skill_service_round_108():
    # Create Agent instance without running __init__
    agent = object.__new__(Agent)

    # Minimal required attributes
    agent.browser_session = types.SimpleNamespace()
    called = {}

    async def fake_get_browser_state_summary(include_screenshot, include_recent_events):
        # record input and return a summary with screenshot
        called['include_screenshot'] = include_screenshot
        called['include_recent_events'] = include_recent_events
        return DummyBrowserStateSummary(url='https://example.com/page', screenshot=b'abc')

    agent.browser_session.get_browser_state_summary = fake_get_browser_state_summary

    # agent.logger now provided by patched class property
    # agent.logger = DummyLogger()  # no longer needed / not allowed

    agent.state = types.SimpleNamespace(n_steps=7, last_model_output=None, last_result=None)
    agent.include_recent_events = True

    # async methods used inside _prepare_context
    async def noop_check_and_update_downloads(context):
        called['checked_downloads'] = context

    async def noop_check_stop_or_pause():
        called['checked_stop_pause'] = True

    async def noop_update_action_models_for_page(url):
        called['updated_action_models_for_page'] = url

    async def noop_maybe_compact_messages(step_info):
        called['maybe_compact_called_with'] = step_info

    async def noop_inject_budget_warning(step_info):
        called['budget_warning_injected'] = step_info

    async def noop_force_done_after_last_step(step_info):
        called['force_done_last'] = True

    async def noop_force_done_after_failure():
        called['force_done_failure'] = True

    # assign async/sync helpers
    agent._check_and_update_downloads = noop_check_and_update_downloads
    agent._log_step_context = lambda bs: called.setdefault('log_step_context', bs)
    agent._check_stop_or_pause = noop_check_stop_or_pause
    agent._update_action_models_for_page = noop_update_action_models_for_page
    agent._maybe_compact_messages = noop_maybe_compact_messages
    agent._inject_budget_warning = noop_inject_budget_warning
    agent._inject_replan_nudge = lambda: called.setdefault('replan_nudge', True)
    agent._inject_exploration_nudge = lambda: called.setdefault('exploration_nudge', True)
    agent._update_loop_detector_page_state = lambda bs: called.setdefault('loop_detector_page_state', bs)
    agent._inject_loop_detection_nudge = lambda: called.setdefault('loop_detection_nudge', True)
    agent._force_done_after_last_step = noop_force_done_after_last_step
    agent._force_done_after_failure = noop_force_done_after_failure

    # settings and other required simple attributes
    agent.tools = DummyTools(prompt_response=[])  # returns falsy list -> should pass None into create_state_messages
    agent.skill_service = None  # triggers branch where unavailable_skills_info stays None
    agent._get_unavailable_skills_info = lambda: (_ for _ in ()).throw(AssertionError("Should not be called"))
    agent._render_plan_description = lambda: 'plan-desc'

    # message manager: prepare_step_state (sync) and create_state_messages (sync)
    captured_prepare = {}
    def prepare_step_state(**kwargs):
        captured_prepare.update(kwargs)
    agent._message_manager = types.SimpleNamespace()
    agent._message_manager.prepare_step_state = prepare_step_state

    captured_create = {}
    def create_state_messages(**kwargs):
        # capture key kwargs for assertions
        captured_create.update(kwargs)
    agent._message_manager.create_state_messages = create_state_messages

    agent.settings = types.SimpleNamespace(use_vision=False)
    agent.sensitive_data = {'s': 1}
    agent.available_file_paths = ['a.txt']

    # Run _prepare_context
    bs = await agent._prepare_context(step_info=None)

    # Assertions: return value, calls and branch behaviors
    assert isinstance(bs, DummyBrowserStateSummary)
    assert bs.screenshot == b'abc'
    # ensure get_browser_state_summary called with include_screenshot=True and include_recent_events propagated
    assert called.get('include_screenshot') is True
    assert called.get('include_recent_events') is True
    # because tools.registry returned falsy list, page_filtered_actions should be None in create_state_messages
    assert 'page_filtered_actions' in captured_create
    assert captured_create['page_filtered_actions'] is None
    # unavailable_skills_info must be None in create_state_messages
    assert captured_create.get('unavailable_skills_info') is None
    # ensure several lifecycle hooks were invoked
    assert called.get('checked_downloads') == f"Step {agent.state.n_steps}: after getting browser state"
    assert called.get('maybe_compact_called_with') is None  # we passed step_info None
    assert called.get('force_done_last') is True
    assert called.get('force_done_failure') is True


@pytest.mark.asyncio
async def test_prepare_context_without_screenshot_with_skill_service_round_108():
    # Prepare a new Agent instance bypassing __init__
    agent = object.__new__(Agent)
    called = {}

    async def fake_get_browser_state_summary(include_screenshot, include_recent_events):
        called['include_screenshot'] = include_screenshot
        called['include_recent_events'] = include_recent_events
        return DummyBrowserStateSummary(url='https://example.org/other', screenshot=None)

    agent.browser_session = types.SimpleNamespace()
    agent.browser_session.get_browser_state_summary = fake_get_browser_state_summary

    # agent.logger provided by patched class property
    agent.state = types.SimpleNamespace(n_steps=3, last_model_output={'m': 1}, last_result={'r': 2})
    agent.include_recent_events = False

    # Async hooks
    async def noop_check_and_update_downloads(context):
        called['checked_downloads'] = context

    async def noop_check_stop_or_pause():
        called['checked_stop_pause'] = True

    async def noop_update_action_models_for_page(url):
        called['updated_action_models_for_page'] = url

    async def noop_maybe_compact_messages(step_info):
        called['maybe_compact_called_with'] = step_info

    async def noop_inject_budget_warning(step_info):
        called['budget_warning_injected'] = step_info

    async def noop_force_done_after_last_step(step_info):
        called['force_done_last'] = True

    async def noop_force_done_after_failure():
        called['force_done_failure'] = True

    agent._check_and_update_downloads = noop_check_and_update_downloads
    agent._log_step_context = lambda bs: called.setdefault('log_step_context', bs)
    agent._check_stop_or_pause = noop_check_stop_or_pause
    agent._update_action_models_for_page = noop_update_action_models_for_page
    agent._maybe_compact_messages = noop_maybe_compact_messages
    agent._inject_budget_warning = noop_inject_budget_warning
    agent._inject_replan_nudge = lambda: called.setdefault('replan_nudge', True)
    agent._inject_exploration_nudge = lambda: called.setdefault('exploration_nudge', True)
    agent._update_loop_detector_page_state = lambda bs: called.setdefault('loop_detector_page_state', bs)
    agent._inject_loop_detection_nudge = lambda: called.setdefault('loop_detection_nudge', True)
    agent._force_done_after_last_step = noop_force_done_after_last_step
    agent._force_done_after_failure = noop_force_done_after_failure

    # tools returns a truthy list of actions -> should be passed through
    agent.tools = DummyTools(prompt_response=['CLICK_BUTTON'])

    # skill_service present -> branch to await _get_unavailable_skills_info
    agent.skill_service = object()
    async def get_unavailable():
        called['unavailable_called'] = True
        return {'missing_skills': ['skill_x']}
    agent._get_unavailable_skills_info = get_unavailable

    agent._render_plan_description = lambda: 'other-plan'

    # message manager
    captured_prepare = {}
    def prepare_step_state(**kwargs):
        captured_prepare.update(kwargs)
    agent._message_manager = types.SimpleNamespace()
    agent._message_manager.prepare_step_state = prepare_step_state

    captured_create = {}
    def create_state_messages(**kwargs):
        captured_create.update(kwargs)
    agent._message_manager.create_state_messages = create_state_messages

    agent.settings = types.SimpleNamespace(use_vision=True)
    agent.sensitive_data = {'s': 2}
    agent.available_file_paths = []

    # Run and assert
    bs = await agent._prepare_context(step_info={'info': 1})

    assert isinstance(bs, DummyBrowserStateSummary)
    assert bs.screenshot is None
    # ensure get_browser_state_summary called with include_screenshot True and include_recent_events False
    assert called.get('include_screenshot') is True
    assert called.get('include_recent_events') is False
    # _get_unavailable_skills_info should have been called and result forwarded into create_state_messages
    assert called.get('unavailable_called') is True
    assert 'unavailable_skills_info' in captured_create
    assert captured_create['unavailable_skills_info'] == {'missing_skills': ['skill_x']}
    # page_filtered_actions should be passed through (truthy list)
    assert captured_create['page_filtered_actions'] == ['CLICK_BUTTON']
    # ensure prepare_step_state was invoked with step_info passed through
    assert captured_prepare.get('step_info') == {'info': 1}
    # lifecycle forced completions executed
    assert called.get('force_done_last') is True
    assert called.get('force_done_failure') is True
