import types
import pytest
from types import SimpleNamespace

import browser_use.agent.service as service

# Helpers used across tests
class FakeLogger:
    def __init__(self):
        self.records = {"debug": [], "info": [], "error": []}

    def debug(self, msg):
        self.records["debug"].append(msg)

    def info(self, msg):
        self.records["info"].append(msg)

    def error(self, msg):
        self.records["error"].append(msg)


class Action:
    def __init__(self, data):
        self._data = data

    def model_dump(self, exclude_unset=True):
        return dict(self._data)


async def _noop_coroutine(*a, **k):
    return None


@pytest.mark.asyncio
async def test_cached_selector_and_done_action_round_025(monkeypatch):
    """
    - Ensure cached selector map path is executed (cached dom_state present).
    - Ensure that a 'done' action is only allowed as a single action and stops processing further actions.
    Observable assertions:
      * tools.act called exactly for the first action only
      * results contains only the first action's result
    """
    logger = FakeLogger()

    # fake browser_session with cached summary and dom_state.selector_map
    class DOMState:
        def __init__(self):
            self.selector_map = {"a": "b"}

    class CachedSummary:
        def __init__(self):
            self.dom_state = DOMState()

    browser_session = SimpleNamespace()
    browser_session._cached_browser_state_summary = CachedSummary()
    browser_session.agent_focus_target_id = "focus"

    async def get_current_page_url():
        return "http://example.com"

    browser_session.get_current_page_url = get_current_page_url

    # fake browser_profile
    browser_profile = SimpleNamespace(wait_between_actions=0)

    # Tools.act should be called for the first action and not for the second
    called = []

    async def fake_act(action, **kwargs):
        called.append(action.model_dump())
        # return an object resembling ActionResult but a simple namespace is fine
        return SimpleNamespace(error=None, is_done=False, success=True, long_term_memory=None, extracted_content=None)

    # registry with no terminating action
    tools = SimpleNamespace()
    tools.act = fake_act
    tools.registry = SimpleNamespace(registry=SimpleNamespace(actions={}))

    # Prepare fake self and bind multi_act
    fake_self = SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = logger
    fake_self.browser_profile = browser_profile
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = []
    fake_self.extraction_schema = None
    fake_self.state = SimpleNamespace(n_steps=1)
    fake_self._check_stop_or_pause = lambda: _noop_coroutine()
    fake_self._log_action = lambda *a, **k: _noop_coroutine()
    fake_self._demo_mode_log = lambda *a, **k: _noop_coroutine()
    fake_self._is_connection_like_error = lambda e: False

    multi_act = types.MethodType(service.Agent.multi_act, fake_self)

    # First action normal, second action contains 'done' metadata which is only allowed as single action
    actions = [Action({"click": {}}), Action({"done": {}})]

    # Patch asyncio.sleep in the module to a no-op to avoid delays
    monkeypatch.setattr(service, "asyncio", service.asyncio)
    monkeypatch.setattr(service.asyncio, "sleep", lambda s: _noop_coroutine())

    results = await multi_act(actions)

    # Assertions
    assert len(results) == 1, "Only the first action should be executed when subsequent action is 'done'"
    assert len(called) == 1 and called[0] == {"click": {}}, "tools.act should be called only for the first action"


@pytest.mark.asyncio
async def test_terminates_sequence_registered_action_round_025(monkeypatch):
    """
    - Ensure that when an action is registered with terminates_sequence=True the sequence stops after that action.
    Observable assertions:
      * the registered action was looked up and the loop exited after first action
      * results contains the first action's result
    """
    logger = FakeLogger()

    browser_session = SimpleNamespace()
    browser_session._cached_browser_state_summary = None
    browser_session.agent_focus_target_id = "f"

    async def get_current_page_url():
        return "http://a"

    browser_session.get_current_page_url = get_current_page_url

    browser_profile = SimpleNamespace(wait_between_actions=0)

    called = []

    async def fake_act(action, **kwargs):
        called.append(action.model_dump())
        return SimpleNamespace(error=None, is_done=False, success=True, long_term_memory=None, extracted_content=None)

    # Make registry return an action descriptor that terminates sequence
    terminating_descriptor = SimpleNamespace(terminates_sequence=True)
    tools = SimpleNamespace()
    tools.act = fake_act
    tools.registry = SimpleNamespace(registry=SimpleNamespace(actions={"my_action": terminating_descriptor}))

    fake_self = SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = logger
    fake_self.browser_profile = browser_profile
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = []
    fake_self.extraction_schema = None
    fake_self.state = SimpleNamespace(n_steps=2)
    fake_self._check_stop_or_pause = lambda: _noop_coroutine()
    fake_self._log_action = lambda *a, **k: _noop_coroutine()
    fake_self._demo_mode_log = lambda *a, **k: _noop_coroutine()
    fake_self._is_connection_like_error = lambda e: False

    multi_act = types.MethodType(service.Agent.multi_act, fake_self)

    # Provide two actions, first named 'my_action' (so registry lookup returns terminating_descriptor)
    actions = [Action({"my_action": {}}), Action({"click": {}})]

    # Patch asyncio.sleep to avoid delays
    monkeypatch.setattr(service, "asyncio", service.asyncio)
    monkeypatch.setattr(service.asyncio, "sleep", lambda s: _noop_coroutine())

    results = await multi_act(actions)

    assert len(results) == 1, "Sequence should stop after an action that terminates the sequence"
    assert called == [{"my_action": {}}], "Only the terminating action should be executed"
    # Check that registry info produced a log mentioning 'terminates sequence'
    assert any("terminates sequence" in m for m in logger.records["info"]), "Logger should note terminating action"


@pytest.mark.asyncio
async def test_exception_during_act_round_025(monkeypatch):
    """
    - When tools.act raises an exception, multi_act should catch it, log, append an ActionResult with the error and return.
    Observable assertions:
      * returned results contain an ActionResult with error text containing the raised exception type and message
    """
    logger = FakeLogger()

    browser_session = SimpleNamespace()
    browser_session._cached_browser_state_summary = None
    browser_session.agent_focus_target_id = "x"

    async def get_current_page_url():
        return "http://x"

    browser_session.get_current_page_url = get_current_page_url

    browser_profile = SimpleNamespace(wait_between_actions=0)

    async def raising_act(action, **kwargs):
        raise ValueError("boom")

    tools = SimpleNamespace()
    tools.act = raising_act
    tools.registry = SimpleNamespace(registry=SimpleNamespace(actions={}))

    fake_self = SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = logger
    fake_self.browser_profile = browser_profile
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = []
    fake_self.extraction_schema = None
    fake_self.state = SimpleNamespace(n_steps=3)
    fake_self._check_stop_or_pause = lambda: _noop_coroutine()
    fake_self._log_action = lambda *a, **k: _noop_coroutine()
    fake_self._demo_mode_log = lambda *a, **k: _noop_coroutine()
    # Ensure connection-like errors are not re-raised
    fake_self._is_connection_like_error = lambda e: False

    multi_act = types.MethodType(service.Agent.multi_act, fake_self)

    actions = [Action({"click": {}})]

    # Run and assert
    results = await multi_act(actions)

    assert len(results) == 1, "On exception the function should return a list with a single ActionResult describing the error"
    res = results[0]
    # The code constructs ActionResult(error=f'{type(e).__name__}: {e}')
    assert getattr(res, "error", None) is not None, "Result should have an error field"
    assert "ValueError: boom" in res.error


@pytest.mark.asyncio
async def test_cached_selector_access_error_round_025():
    """
    - Simulate an exception when accessing _cached_browser_state_summary to hit the except branch that logs an error and sets cached_selector_map to {}.
    Observable assertions:
      * function completes and returns [] when no actions provided
      * logger.error was called about getting cached selector map
    """
    logger = FakeLogger()

    class BrowserSessionErrorOnAccess:
        @property
        def _cached_browser_state_summary(self):
            raise RuntimeError("boom access")

        agent_focus_target_id = None

        async def get_current_page_url(self):
            return "about:blank"

    browser_session = BrowserSessionErrorOnAccess()

    browser_profile = SimpleNamespace(wait_between_actions=0)

    tools = SimpleNamespace()
    tools.act = lambda *a, **k: _noop_coroutine()
    tools.registry = SimpleNamespace(registry=SimpleNamespace(actions={}))

    fake_self = SimpleNamespace()
    fake_self.browser_session = browser_session
    fake_self.logger = logger
    fake_self.browser_profile = browser_profile
    fake_self.tools = tools
    fake_self.file_system = None
    fake_self.settings = SimpleNamespace(page_extraction_llm=None)
    fake_self.sensitive_data = None
    fake_self.available_file_paths = []
    fake_self.extraction_schema = None
    fake_self.state = SimpleNamespace(n_steps=0)
    fake_self._check_stop_or_pause = lambda: _noop_coroutine()
    fake_self._log_action = lambda *a, **k: _noop_coroutine()
    fake_self._demo_mode_log = lambda *a, **k: _noop_coroutine()
    fake_self._is_connection_like_error = lambda e: False

    multi_act = types.MethodType(service.Agent.multi_act, fake_self)

    results = await multi_act([])

    assert results == [], "No actions -> empty results"
    # Expect that an error about getting cached selector map was logged
    assert any("Error getting cached selector map" in m for m in logger.records["error"]), "Cached selector access error should be logged"
