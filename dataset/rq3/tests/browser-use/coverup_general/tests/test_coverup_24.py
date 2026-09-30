# file: browser_use/agent/service.py:2717-2837
# asked: {"lines": [2728, 2729, 2731, 2732, 2734, 2735, 2737, 2739, 2740, 2741, 2742, 2744, 2746, 2747, 2749, 2751, 2752, 2753, 2754, 2757, 2758, 2759, 2761, 2762, 2765, 2768, 2769, 2771, 2772, 2773, 2774, 2775, 2776, 2777, 2778, 2781, 2782, 2783, 2784, 2785, 2787, 2788, 2789, 2790, 2791, 2792, 2793, 2796, 2798, 2799, 2804, 2805, 2806, 2807, 2809, 2812, 2813, 2815, 2816, 2817, 2819, 2821, 2822, 2824, 2825, 2827, 2828, 2829, 2830, 2831, 2834, 2835, 2837], "branches": [[2733, 2737], [2733, 2739], [2744, 2746], [2744, 2837], [2749, 2751], [2749, 2757], [2751, 2752], [2751, 2757], [2757, 2758], [2757, 2761], [2781, 2782], [2781, 2787], [2787, 2788], [2787, 2796], [2798, 2799], [2798, 2804], [2805, 2806], [2805, 2812], [2815, 2744], [2815, 2816], [2821, 2822], [2821, 2824], [2824, 2825], [2824, 2827]]}
# gained: {"lines": [2728, 2729, 2731, 2732, 2734, 2735, 2737, 2739, 2744, 2746, 2747, 2749, 2751, 2752, 2753, 2754, 2757, 2761, 2762, 2765, 2768, 2769, 2771, 2772, 2773, 2774, 2775, 2776, 2777, 2778, 2781, 2787, 2796, 2798, 2804, 2805, 2806, 2807, 2809, 2812, 2813, 2815, 2816, 2817, 2819, 2821, 2822, 2824, 2825, 2827, 2828, 2829, 2830, 2831, 2834, 2835, 2837], "branches": [[2733, 2737], [2733, 2739], [2744, 2746], [2749, 2751], [2749, 2757], [2751, 2752], [2757, 2761], [2781, 2787], [2787, 2796], [2798, 2804], [2805, 2806], [2805, 2812], [2815, 2744], [2815, 2816], [2821, 2822], [2821, 2824], [2824, 2825], [2824, 2827]]}

import asyncio
import logging
from types import SimpleNamespace

import pytest

from browser_use.agent.service import Agent
from browser_use.agent.views import ActionResult


class FakeActionModel:
    def __init__(self, data: dict):
        self._data = data

    def model_dump(self, exclude_unset=True):
        return dict(self._data)


class FakeBrowserSession:
    def __init__(self, urls=None, focus_sequence=None, cached_selector_map=None, wait_between_actions=0.0):
        # urls: iterable or list of values to return on successive get_current_page_url calls
        self._urls = list(urls) if urls is not None else ['about:blank']
        self._url_call_count = 0
        self.agent_focus_target_id = None if not focus_sequence else focus_sequence[0]
        self._focus_sequence = list(focus_sequence) if focus_sequence is not None else None
        # Simulate cached browser state summary
        if cached_selector_map is not None:
            dom_state = SimpleNamespace(selector_map=cached_selector_map)
            self._cached_browser_state_summary = SimpleNamespace(dom_state=dom_state)
        else:
            self._cached_browser_state_summary = None
        # minimal profile to satisfy attribute access in tests
        self.browser_profile = SimpleNamespace(wait_between_actions=wait_between_actions, demo_mode=False, downloads_path=None)
        # store last seen url for debugging if needed
        self._last_url = None

    async def get_current_page_url(self):
        # return successive values if provided, else always return the last
        if self._url_call_count < len(self._urls):
            val = self._urls[self._url_call_count]
        else:
            val = self._urls[-1]
        self._url_call_count += 1
        self._last_url = val
        # update focus if sequence provided
        if self._focus_sequence is not None:
            idx = min(self._url_call_count - 1, len(self._focus_sequence) - 1)
            self.agent_focus_target_id = self._focus_sequence[idx]
        return val


class FakeTools:
    def __init__(self, act_behavior=None, registry_actions=None):
        # act_behavior: either a callable(action, ...) returning ActionResult or raising
        # if None, return a default successful ActionResult (with success=None for non-done)
        self._act_behavior = act_behavior
        self.registry = SimpleNamespace(registry=SimpleNamespace(actions=registry_actions or {}))

    async def act(self, **kwargs):
        if callable(self._act_behavior):
            return await self._act_behavior(**kwargs)
        # default success for a regular action: is_done=False, success must be None per model validation
        return ActionResult(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=None)


class DummyAgent(Agent):
    """Minimal Agent subclass that doesn't run full __init__; sets just the attributes multi_act uses."""

    def __init__(self):
        # Do not call super().__init__
        # Attributes required by multi_act
        self.browser_session = None
        self.file_system = None
        self.settings = SimpleNamespace(page_extraction_llm=None)
        self.sensitive_data = None
        self.available_file_paths = []
        self.extraction_schema = None
        self.tools = None
        self.state = SimpleNamespace(n_steps=1)
        self._demo_mode_enabled = False
        self._external_pause_event = asyncio.Event()
        self._external_pause_event.set()

        # behavior toggles for tests
        self._is_connection_like_error_flag = False

        # simple logger
        self._logger = logging.getLogger(f"DummyAgent_{id(self)}")
        self._logger.addHandler(logging.NullHandler())

    @property
    def logger(self):
        return self._logger

    async def _check_stop_or_pause(self):
        # default: no stop
        return None

    async def _log_action(self, action, action_name, action_num, total_actions):
        # no-op for testing
        return None

    async def _demo_mode_log(self, message: str, level: str = "info", metadata: dict | None = None):
        # no-op for testing
        return None

    def _is_connection_like_error(self, error: Exception) -> bool:
        return self._is_connection_like_error_flag


@pytest.mark.asyncio
async def test_multi_act_terminates_sequence_and_cached_selector_map(monkeypatch):
    # Ensure asyncio.sleep is a no-op to avoid delays if triggered
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    agent = DummyAgent()
    # Create a browser session that has a cached selector map to exercise that branch
    agent.browser_session = FakeBrowserSession(cached_selector_map={"sel": "val"}, wait_between_actions=0.0)
    # Tools: first action 'navigate' is registered as terminates_sequence
    registry_actions = {
        "navigate": SimpleNamespace(terminates_sequence=True),
        "click": SimpleNamespace(terminates_sequence=False),
    }

    # act returns a successful ActionResult for the first action (non-done => success=None)
    async def act_behavior(action, browser_session, file_system, page_extraction_llm, sensitive_data, available_file_paths, extraction_schema):
        return ActionResult(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=None)

    agent.tools = FakeTools(act_behavior=act_behavior, registry_actions=registry_actions)

    actions = [FakeActionModel({"navigate": {"url": "http://example.com"}}),
               FakeActionModel({"click": {"selector": "#btn"}})]

    results = await agent.multi_act(actions)
    # Should run first action and then stop due to terminates_sequence -> only 1 result
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].error is None
    assert results[0].is_done is False


@pytest.mark.asyncio
async def test_multi_act_runtime_page_change_detection(monkeypatch):
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    agent = DummyAgent()
    # Browser session: first call returns url1, second returns url2 to simulate page change
    agent.browser_session = FakeBrowserSession(urls=["http://a", "http://b"], focus_sequence=[None, None], wait_between_actions=0.0)

    registry_actions = {
        "click": SimpleNamespace(terminates_sequence=False),
        "click2": SimpleNamespace(terminates_sequence=False),
    }

    async def act_behavior(action, browser_session, file_system, page_extraction_llm, sensitive_data, available_file_paths, extraction_schema):
        # Simulate action succeeded but not done; success must be None
        return ActionResult(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=None)

    agent.tools = FakeTools(act_behavior=act_behavior, registry_actions=registry_actions)

    actions = [FakeActionModel({"click": {"selector": "a"}}),
               FakeActionModel({"click2": {"selector": "b"}})]

    results = await agent.multi_act(actions)
    # Should detect runtime page change and break after first action
    assert len(results) == 1
    assert results[0].error is None


@pytest.mark.asyncio
async def test_multi_act_exception_during_action_appends_error_and_returns(monkeypatch):
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    agent = DummyAgent()
    agent.browser_session = FakeBrowserSession(wait_between_actions=0.0)

    registry_actions = {
        "boom": SimpleNamespace(terminates_sequence=False),
    }

    async def act_behavior(action, browser_session, file_system, page_extraction_llm, sensitive_data, available_file_paths, extraction_schema):
        raise Exception("boom happened")

    agent.tools = FakeTools(act_behavior=act_behavior, registry_actions=registry_actions)
    # Ensure _is_connection_like_error returns False so multi_act handles the exception
    agent._is_connection_like_error_flag = False

    actions = [FakeActionModel({"boom": {}})]
    results = await agent.multi_act(actions)
    # Should append an ActionResult with error describing the exception and return immediately
    assert len(results) == 1
    assert results[0].error is not None
    assert "Exception" in results[0].error and "boom happened" in results[0].error


@pytest.mark.asyncio
async def test_multi_act_connection_like_error_reraises(monkeypatch):
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    agent = DummyAgent()
    agent.browser_session = FakeBrowserSession(wait_between_actions=0.0)

    registry_actions = {"conn": SimpleNamespace(terminates_sequence=False)}

    async def act_behavior(action, browser_session, file_system, page_extraction_llm, sensitive_data, available_file_paths, extraction_schema):
        raise Exception("connection lost")

    agent.tools = FakeTools(act_behavior=act_behavior, registry_actions=registry_actions)
    # Make the agent treat the exception as connection-like so it will re-raise
    agent._is_connection_like_error_flag = True

    actions = [FakeActionModel({"conn": {}})]
    with pytest.raises(Exception) as excinfo:
        await agent.multi_act(actions)
    assert "connection lost" in str(excinfo.value)


@pytest.mark.asyncio
async def test_multi_act_interrupted_error_reraises(monkeypatch):
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    agent = DummyAgent()
    agent.browser_session = FakeBrowserSession(wait_between_actions=0.0)

    # Make _check_stop_or_pause raise InterruptedError when called
    async def _raise_interrupted():
        raise InterruptedError("stopped")

    agent._check_stop_or_pause = _raise_interrupted

    # Tools should not be called, but provide a registry mapping
    agent.tools = FakeTools(act_behavior=None, registry_actions={})

    actions = [FakeActionModel({"any": {}})]
    with pytest.raises(InterruptedError):
        await agent.multi_act(actions)


@pytest.mark.asyncio
async def test_multi_act_done_action_allowed_only_single(monkeypatch):
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    agent = DummyAgent()
    agent.browser_session = FakeBrowserSession(wait_between_actions=0.0)

    registry_actions = {"first": SimpleNamespace(terminates_sequence=False), "done": SimpleNamespace(terminates_sequence=False)}

    async def act_behavior(action, browser_session, file_system, page_extraction_llm, sensitive_data, available_file_paths, extraction_schema):
        # first action returns success (non-done => success=None)
        return ActionResult(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=None)

    agent.tools = FakeTools(act_behavior=act_behavior, registry_actions=registry_actions)

    actions = [FakeActionModel({"first": {"x": 1}}), FakeActionModel({"done": {"result": "ok"}})]
    results = await agent.multi_act(actions)
    # The 'done' action should be detected as disallowed when not single and break before execution.
    # So only the first action should be executed.
    assert len(results) == 1
    assert results[0].error is None
