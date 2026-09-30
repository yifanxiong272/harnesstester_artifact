import asyncio
import types
import pytest

from browser_use.agent import service as service_mod

# Helpers / fakes used across tests
class DummyLogger:
    def __init__(self):
        self.records = {"error": [], "debug": [], "info": []}

    def error(self, msg):
        self.records["error"].append(msg)

    def debug(self, msg):
        self.records["debug"].append(msg)

    def info(self, msg):
        self.records["info"].append(msg)


class DummyBrowserStateSummary:
    def __init__(self, selector_map=None):
        class DomState:
            def __init__(self, selector_map):
                self.selector_map = selector_map

        self.dom_state = DomState(selector_map or {})


class DummyBrowserSession:
    def __init__(self, urls=None, focus_ids=None, cached_summary=None, raise_on_cached=False):
        # urls: iterable to yield pre/post urls per call
        self._urls = list(urls or ["http://start"])
        self._focus = list(focus_ids or [None])
        self.index = 0
        self.agent_focus_target_id = self._focus[0] if self._focus else None
        self._cached_browser_state_summary = cached_summary
        self._raise_on_cached = raise_on_cached

    async def get_current_page_url(self):
        # return current and then increment index to simulate change
        val = self._urls[min(self.index, len(self._urls) - 1)]
        return val

    def __getattribute__(self, name):
        # allow simulating an exception when accessing cached summary
        if name == "_cached_browser_state_summary":
            if object.__getattribute__(self, "_raise_on_cached"):
                raise RuntimeError("cached access failed")
        return object.__getattribute__(self, name)


class DummyBrowserProfile:
    def __init__(self, wait_between_actions=0):
        self.wait_between_actions = wait_between_actions


class DummyRegistry:
    def __init__(self, actions_map):
        self.actions = actions_map


class DummyTools:
    def __init__(self, act_coro, registry_map=None):
        self.act_called = []
        self._act_coro = act_coro
        self.registry = types.SimpleNamespace(registry=DummyRegistry(registry_map or {}))

    async def act(self, **kwargs):
        self.act_called.append(kwargs)
        return await self._act_coro(**kwargs)


class StubAction:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self, exclude_unset=True):
        # Respect the method signature used by multi_act
        return dict(self._payload)


async def _nop_async(*a, **kw):
    return None


@pytest.mark.asyncio
async def test_done_as_non_first_action_breaks_round_024(monkeypatch):
    """If a non-first action declares 'done', multi_act should stop before executing it."""
    logger = DummyLogger()

    # first action is normal; second action declares 'done'
    actions = [StubAction({"click": {}}), StubAction({"done": True})]

    # act coroutine that would record if invoked
    async def act_coro(action, **kwargs):
        return types.SimpleNamespace(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=True)

    tools = DummyTools(act_coro, registry_map={})

    fake_self = types.SimpleNamespace()
    fake_self.browser_session = DummyBrowserSession(urls=["a", "a"], focus_ids=[None, None], cached_summary=None)
    fake_self.browser_profile = DummyBrowserProfile(wait_between_actions=0)
    fake_self._check_stop_or_pause = _nop_async
    fake_self._log_action = _nop_async
    fake_self._demo_mode_log = _nop_async
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = types.SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = None
    fake_self.extraction_schema = None
    fake_self.logger = logger
    fake_self.state = types.SimpleNamespace(n_steps=0)
    fake_self._is_connection_like_error = lambda e: False

    bound = service_mod.Agent.multi_act.__get__(fake_self, service_mod.Agent)
    results = await bound(actions)

    # Only the first action should have been executed, so tools.act called once
    assert len(tools.act_called) == 1, "Second action (done) should not be executed when not first"
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_registered_action_terminates_sequence_round_024(monkeypatch):
    """When a registered action has terminates_sequence True, remaining actions are skipped."""
    logger = DummyLogger()

    # two actions so i>0 branch is reachable
    actions = [StubAction({"click": {}}), StubAction({"click": {}})]

    async def act_coro(action, **kwargs):
        # return a benign result so the post-action checks proceed
        return types.SimpleNamespace(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=True)

    # Prepare registry entry with terminates_sequence True for action name 'click'
    registered = types.SimpleNamespace(terminates_sequence=True)
    tools = DummyTools(act_coro, registry_map={"click": registered})

    fake_self = types.SimpleNamespace()
    # cached summary present to exercise cached_selector_map branch
    fake_self.browser_session = DummyBrowserSession(urls=["same", "same"], focus_ids=[None, None], cached_summary=DummyBrowserStateSummary({"a":"b"}))
    fake_self.browser_profile = DummyBrowserProfile(wait_between_actions=0)
    fake_self._check_stop_or_pause = _nop_async
    fake_self._log_action = _nop_async
    fake_self._demo_mode_log = _nop_async
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = types.SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = None
    fake_self.extraction_schema = None
    fake_self.logger = logger
    fake_self.state = types.SimpleNamespace(n_steps=1)
    fake_self._is_connection_like_error = lambda e: False

    bound = service_mod.Agent.multi_act.__get__(fake_self, service_mod.Agent)
    results = await bound(actions)

    # Tools.act should be called for the first action and then sequence terminated by registry flag
    assert len(tools.act_called) == 1
    # ensure logger recorded the info about termination
    found = any("terminates sequence" in m for m in logger.records["info"]) or any("terminates sequence" in m for m in logger.records.get("debug", []))
    assert found or len(results) == 1


@pytest.mark.asyncio
async def test_runtime_page_change_detection_round_024(monkeypatch):
    """If page URL or focus changes after an action, remaining actions are skipped."""
    logger = DummyLogger()

    # two actions; second should be skipped due to runtime change
    actions = [StubAction({"click": {}}), StubAction({"click": {}})]

    async def act_coro(action, **kwargs):
        return types.SimpleNamespace(error=None, is_done=False, long_term_memory=None, extracted_content=None, success=True)

    tools = DummyTools(act_coro, registry_map={})

    fake_self = types.SimpleNamespace()
    # Simulate URL changing between pre and post action by setting browser_session.get_current_page_url to yield different values
    class ChangingSession(DummyBrowserSession):
        def __init__(self):
            super().__init__(urls=["url_before", "url_after"], focus_ids=[None, None], cached_summary=None)

        async def get_current_page_url(self):
            # return first time 'url_before', next call 'url_after'
            res = self._urls[self.index]
            # increment index so next call returns changed URL
            self.index = min(self.index + 1, len(self._urls) - 1)
            return res

    fake_self.browser_session = ChangingSession()
    fake_self.browser_profile = DummyBrowserProfile(wait_between_actions=0)
    fake_self._check_stop_or_pause = _nop_async
    fake_self._log_action = _nop_async
    fake_self._demo_mode_log = _nop_async
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = types.SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = None
    fake_self.extraction_schema = None
    fake_self.logger = logger
    fake_self.state = types.SimpleNamespace(n_steps=0)
    fake_self._is_connection_like_error = lambda e: False

    bound = service_mod.Agent.multi_act.__get__(fake_self, service_mod.Agent)
    results = await bound(actions)

    # Only the first action executed, because URL changed after it
    assert len(tools.act_called) == 1
    assert any("Page changed" in m or "Page changed" in m for m in logger.records["info"]) or len(results) == 1


@pytest.mark.asyncio
async def test_tools_act_raises_exception_appends_error_round_024(monkeypatch):
    """If tools.act raises an exception, multi_act should append an ActionResult with the error and return."""
    logger = DummyLogger()

    actions = [StubAction({"click": {}})]

    async def act_coro(action, **kwargs):
        raise ValueError("boom")

    tools = DummyTools(act_coro, registry_map={})

    fake_self = types.SimpleNamespace()
    fake_self.browser_session = DummyBrowserSession(urls=["x"], focus_ids=[None], cached_summary=None)
    fake_self.browser_profile = DummyBrowserProfile(wait_between_actions=0)
    fake_self._check_stop_or_pause = _nop_async
    fake_self._log_action = _nop_async
    fake_self._demo_mode_log = _nop_async
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = types.SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = None
    fake_self.extraction_schema = None
    fake_self.logger = logger
    fake_self.state = types.SimpleNamespace(n_steps=0)

    # _is_connection_like_error should return False to hit generic exception handling
    fake_self._is_connection_like_error = lambda e: False

    bound = service_mod.Agent.multi_act.__get__(fake_self, service_mod.Agent)
    results = await bound(actions)

    # Should return a list with an ActionResult-like object that has an error attribute containing ValueError
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    # error may be a string constructed by the function
    err = getattr(item, "error", None)
    assert err is not None
    assert "ValueError" in str(err) or "boom" in str(err)
