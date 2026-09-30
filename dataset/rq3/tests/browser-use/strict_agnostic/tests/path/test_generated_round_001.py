import asyncio
from types import SimpleNamespace
import pytest

from browser_use.tools.service import Tools

# Minimal fake event that is awaitable and provides async event_result()
class FakeEvent:
    def __init__(self, result=None, raise_exc=None):
        self._result = result
        self._raise_exc = raise_exc

    def __await__(self):
        async def _inner():
            return None
        return _inner().__await__()

    async def event_result(self, *args, **kwargs):
        if self._raise_exc:
            raise self._raise_exc
        return self._result


class FakeTab:
    def __init__(self, target_id: str):
        self.target_id = target_id


class FakeEventBus:
    def __init__(self, session):
        # mapping from event type name -> result to return from event_result()
        self.session = session
        self.event_results = {}

    def dispatch(self, event):
        name = type(event).__name__
        # Return an awaitable FakeEvent whose event_result yields a configured value
        # Default: return a successful empty metadata result
        result = None
        raise_exc = None
        if name in self.event_results:
            value = self.event_results[name]
            # allow configured exceptions
            if isinstance(value, Exception):
                raise_exc = value
            else:
                result = value
        return FakeEvent(result=result, raise_exc=raise_exc)


class FakeBrowserSession:
    def __init__(self, *, tabs_sequence=None, llm_screenshot_size=None, original_viewport=None, is_local=True):
        # tabs_sequence: list of lists to return on successive get_tabs() calls
        self._tabs_sequence = tabs_sequence or [[]]
        self._tabs_calls = 0
        self.llm_screenshot_size = llm_screenshot_size
        self._original_viewport_size = original_viewport
        self.is_local = is_local
        self.downloaded_files = []
        self.event_bus = FakeEventBus(self)
        # a no-op logger compatible with used attributes
        class _Logger:
            def info(self, *_args, **_kwargs):
                pass
            def error(self, *_args, **_kwargs):
                pass
            def warning(self, *_args, **_kwargs):
                pass
            def debug(self, *_args, **_kwargs):
                pass
        self.logger = _Logger()

    async def get_tabs(self):
        # return next sequence element (if out of range, always last)
        idx = min(self._tabs_calls, len(self._tabs_sequence) - 1)
        self._tabs_calls += 1
        return [FakeTab(t) for t in self._tabs_sequence[idx]]

    async def highlight_coordinate_click(self, x, y):
        # no-op async method used by create_task
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_click_by_coordinate_missing_coords_round_001():
    """When coordinate_x/coordinate_y are missing, the action returns an error ActionResult."""
    tools = Tools()

    # params with missing coordinates
    params = SimpleNamespace(coordinate_x=None, coordinate_y=None)

    session = FakeBrowserSession(tabs_sequence=[[]])

    res = await tools._click_by_coordinate(params, session)

    # Expect an ActionResult-like object with an error attribute
    assert hasattr(res, 'error')
    assert res.error is not None
    assert 'Both coordinate_x and coordinate_y must be provided' in res.error


@pytest.mark.asyncio
async def test_click_by_coordinate_conversion_and_new_tab_round_001():
    """Coordinates should be converted when llm_screenshot_size and original viewport are provided.
    Also detect and report that a new tab was opened and auto-switched.
    """
    tools = Tools()

    # Prepare a browser session that initially has one tab and then a new one appears
    initial_tab = 'tab_initial_0001'
    new_tab = 'tab_new_5678'
    tabs_sequence = [
        [initial_tab],  # first get_tabs() call (tabs_before)
        [initial_tab, new_tab],  # second get_tabs() call (tabs_after) inside _detect_new_tab_opened
    ]

    session = FakeBrowserSession(tabs_sequence=tabs_sequence, llm_screenshot_size=(100, 200), original_viewport=(1000, 800))

    # Configure event results: ClickCoordinateEvent returns metadata dict (no validation_error)
    # SwitchTabEvent should succeed (no exception)
    session.event_bus.event_results['ClickCoordinateEvent'] = {'info': 'clicked'}
    session.event_bus.event_results['SwitchTabEvent'] = None

    params = SimpleNamespace(coordinate_x=10, coordinate_y=20)

    res = await tools._click_by_coordinate(params, session)

    assert getattr(res, 'error', None) is None
    # metadata should contain converted coordinates (actual_x = int((10/100)*1000)=100, actual_y=int((20/200)*800)=80)
    assert isinstance(res.metadata, dict)
    assert res.metadata.get('click_x') == 100
    assert res.metadata.get('click_y') == 80

    # extracted_content / memory should include the original coordinates text
    assert 'Clicked on coordinate' in res.extracted_content
    # And the returned memory should mention switching to new tab
    assert 'Automatically switched to new tab' in res.extracted_content or 'This opened a new tab' in res.extracted_content


@pytest.mark.asyncio
async def test_click_by_coordinate_validation_error_round_001():
    """If the click handler returns a dict with 'validation_error', the ActionResult returns that error."""
    tools = Tools()

    session = FakeBrowserSession(tabs_sequence=[[]])
    # Simulate the click handler returning a validation error
    session.event_bus.event_results['ClickCoordinateEvent'] = {'validation_error': 'Cannot click on <select> elements.'}

    params = SimpleNamespace(coordinate_x=50, coordinate_y=60)

    res = await tools._click_by_coordinate(params, session)

    assert getattr(res, 'error', None) is not None
    assert 'Cannot click on <select> elements.' in res.error
