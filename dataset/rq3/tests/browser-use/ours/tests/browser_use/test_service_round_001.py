import asyncio
from types import SimpleNamespace

import pytest

from browser_use.tools.service import Tools
from browser_use.agent.views import ActionResult


class DummyEvent:
    def __init__(self, result=None, raise_on_event_result: Exception | None = None):
        self._result = result
        self._raise_on_event_result = raise_on_event_result

    def __await__(self):
        async def _inner():
            return self
        return _inner().__await__()

    async def event_result(self, *args, **kwargs):
        # optional simulated exception path
        if isinstance(self._raise_on_event_result, Exception):
            raise self._raise_on_event_result
        return self._result


class DummyEventBus:
    def __init__(self, event_to_return: DummyEvent):
        self._event = event_to_return
        # record last dispatch args for debugging if needed
        self.last_dispatch_args = None

    def dispatch(self, *args, **kwargs):
        # return a coroutine that yields the DummyEvent when awaited (matches code usage: event = dispatch(...); await event)
        self.last_dispatch_args = (args, kwargs)

        async def _inner():
            return self._event

        return _inner()


class SimpleLogger:
    def __init__(self):
        self.messages = {"info": [], "warning": [], "error": [], "debug": []}

    def info(self, msg):
        self.messages["info"].append(msg)

    def warning(self, msg):
        self.messages["warning"].append(msg)

    def error(self, msg):
        self.messages["error"].append(msg)

    def debug(self, msg):
        self.messages["debug"].append(msg)


class FakeTab:
    def __init__(self, target_id: str):
        self.target_id = target_id


class FakeBrowserSession:
    def __init__(self, *, get_tabs_sequence=None, event_to_return: DummyEvent | None = None,
                 llm_screenshot_size=None, original_viewport_size=None,
                 is_local=True):
        # get_tabs_sequence: list of lists to return on successive await get_tabs() calls
        self._get_tabs_sequence = list(get_tabs_sequence or [[]])
        self.event_bus = DummyEventBus(event_to_return or DummyEvent(result=None))
        self.llm_screenshot_size = llm_screenshot_size
        # private attribute name as in source
        self._original_viewport_size = original_viewport_size
        self.downloaded_files = []
        self.is_local = is_local
        self.logger = SimpleLogger()

    async def get_tabs(self):
        # pop the next sequence return if available, otherwise return last
        if self._get_tabs_sequence:
            seq = self._get_tabs_sequence.pop(0)
            return [FakeTab(tid) for tid in seq]
        return []

    async def highlight_coordinate_click(self, x, y):
        # simulate a quick non-blocking highlight; do nothing
        return None

    # helpers used by other code paths when needed
    async def get_element_by_index(self, idx):
        return None

    async def get_or_create_cdp_session(self, *args, **kwargs):
        class DummyCDP:
            session_id = 'session'
            class cdp_client:
                @staticmethod
                async def send(*args, **kwargs):
                    return {}
        return DummyCDP()

    async def take_screenshot(self, full_page=False):
        return b"PNGDATA"

    async def get_current_page_url(self):
        return "https://example.local/"

    async def get_current_page_title(self):
        return "Title"


# Test 1: missing coordinates produces immediate ActionResult with error
def test_click_by_coordinate_missing_coordinates_round_001():
    tools = Tools()
    # params object lacking coordinates
    params = SimpleNamespace(coordinate_x=None, coordinate_y=None)
    browser_session = FakeBrowserSession(get_tabs_sequence=[[]], event_to_return=DummyEvent(result=None))

    result = asyncio.run(tools._click_by_coordinate(params, browser_session))

    assert isinstance(result, ActionResult)
    assert result.error is not None
    assert 'Both coordinate_x and coordinate_y must be provided' in result.error


# Test 2: conversion from LLM screenshot size to viewport size happens when both sizes are set
def test_click_by_coordinate_conversion_round_001():
    tools = Tools()
    # Coordinates in LLM screenshot space
    params = SimpleNamespace(coordinate_x=50, coordinate_y=50)

    # Prepare event that returns click metadata (no validation_error)
    # We'll verify metadata contains converted coordinates
    # For this test, ensure no new tabs appear (same tabs before/after)
    event = DummyEvent(result={'info': 'ok'})

    # Browser: llm size 100x100 -> original viewport 200x400 => expected converted (100, 200)
    browser_session = FakeBrowserSession(
        get_tabs_sequence=[[], []],  # first call for tabs_before, second call later (no new tabs)
        event_to_return=event,
        llm_screenshot_size=(100, 100),
        original_viewport_size=(200, 400),
    )

    result = asyncio.run(tools._click_by_coordinate(params, browser_session))

    assert isinstance(result, ActionResult)
    # original message uses the LLM coords in the memory string
    assert 'Clicked on coordinate 50, 50' in (result.extracted_content or '')
    # metadata should contain converted viewport coordinates (actual_x, actual_y)
    assert isinstance(result.metadata, dict)
    assert result.metadata.get('click_x') == 100
    assert result.metadata.get('click_y') == 200


# Test 3: clicking that opens a new tab but switching raises -> should include note about opened tab
def test_click_by_coordinate_new_tab_switch_fail_round_001():
    tools = Tools()
    params = SimpleNamespace(coordinate_x=10, coordinate_y=20)

    # Simulate an event that completes normally
    event = DummyEvent(result={'info': 'ok'})

    # Browser session will return one tab at first call, then two tabs (new one) on second
    before_tab_id = 'target_aaaa1111'
    new_tab_id = 'target_newtab9999'

    # Prepare FakeBrowserSession where event_bus.dispatch for the switch will raise on await
    # We'll inject an event for the initial ClickCoordinateEvent (normal), but the SwitchTabEvent dispatch
    # inside _detect_new_tab_opened will require the event_bus to return a DummyEvent that raises when awaited

    # The main click dispatch returns event (event)
    # For switch, we will monkeypatch the dispatch method after construction to return an event that raises
    browser_session = FakeBrowserSession(
        get_tabs_sequence=[[before_tab_id], [before_tab_id, new_tab_id]],
        event_to_return=event,
    )

    # Replace the event_bus.dispatch to behave conditionally based on call args: if SwitchTabEvent-like arg present -> return event that raises
    original_dispatch = browser_session.event_bus.dispatch

    def conditional_dispatch(*args, **kwargs):
        # args[0] is the event instance constructed in code, we can't rely on type, so examine repr for 'target_id' string
        if args and 'SwitchTabEvent' in repr(args[0]) or (args and getattr(args[0], 'target_id', None) == new_tab_id):
            # return a coroutine that when awaited yields an event whose event_result raises
            raise_event = DummyEvent(result=None, raise_on_event_result=Exception('switch failed'))

            async def _inner():
                return raise_event

            return _inner()
        # default
        return original_dispatch(*args, **kwargs)

    # Patch dispatch
    browser_session.event_bus.dispatch = conditional_dispatch

    result = asyncio.run(tools._click_by_coordinate(params, browser_session))

    assert isinstance(result, ActionResult)
    # The memory message should include the note about an opened new tab (tab_id last 4 chars)
    text = result.extracted_content or ''
    assert 'Clicked on coordinate 10, 20' in text
    assert 'opened a new tab' in text or 'switched to new tab' in text or 'Note: This opened a new tab' in text or '(tab_id:' in text


# Test 4: click by index with index=0 triggers the assertion branch and returns an ActionResult with error
def test_click_by_index_index_zero_round_001():
    tools = Tools()
    params = SimpleNamespace(index=0)
    browser_session = FakeBrowserSession(get_tabs_sequence=[[]], event_to_return=DummyEvent(result=None))

    result = asyncio.run(tools._click_by_index(params, browser_session))

    assert isinstance(result, ActionResult)
    # Should return an error message about failing to click element 0
    assert result.error is not None
    assert 'Failed to click element' in result.error or 'Cannot click on element with index 0' in (result.error or '')
