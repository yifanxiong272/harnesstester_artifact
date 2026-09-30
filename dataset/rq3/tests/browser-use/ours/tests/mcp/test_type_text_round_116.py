import asyncio
import pytest

from browser_use.mcp.server import BrowserUseServer

# Patch target module symbol where _type_text will import from
import browser_use.browser.events as events_module

class DummyTypeTextEvent:
    def __init__(self, node, text, is_sensitive, sensitive_key_name):
        self.node = node
        self.text = text
        self.is_sensitive = is_sensitive
        self.sensitive_key_name = sensitive_key_name

# Simple fake event bus that records the dispatched event and returns an awaitable
class FakeEventBus:
    def __init__(self):
        self.last_event = None

    def dispatch(self, event):
        # record the event object that was dispatched
        self.last_event = event

        async def _noop():
            # simulate an asynchronous event handling completion
            return None

        return _noop()

# Fake browser session with controllable element return
class FakeSession:
    def __init__(self, element):
        self._element = element
        self.event_bus = FakeEventBus()

    async def get_dom_element_by_index(self, index):
        # simulate async retrieval of an element
        await asyncio.sleep(0)
        return self._element


# Ensure the function-local import inside _type_text resolves to our dummy event type
events_module.TypeTextEvent = DummyTypeTextEvent

@pytest.mark.asyncio
async def test_no_browser_session_round_116():
    server = BrowserUseServer(session_timeout_minutes=30)
    # explicitly ensure no session
    server.browser_session = None

    result = await server._type_text(1, "hello")
    assert result == 'Error: No browser session active'


@pytest.mark.asyncio
async def test_element_not_found_round_116():
    server = BrowserUseServer(session_timeout_minutes=30)
    # session returns no element
    server.browser_session = FakeSession(element=None)

    idx = 5
    result = await server._type_text(idx, "irrelevant")
    assert result == f'Element with index {idx} not found'


@pytest.mark.asyncio
async def test_non_sensitive_text_dispatch_and_return_round_116():
    server = BrowserUseServer(session_timeout_minutes=30)
    # element exists (could be any object)
    element_obj = {"node": "node-1"}
    session = FakeSession(element=element_obj)
    server.browser_session = session

    text = "short"  # len < 6 -> not potentially sensitive
    result = await server._type_text(1, text)

    # Return value should reflect non-sensitive branch
    assert result == "Typed 'short' into element 1"

    # Event bus should have recorded a dispatch with the expected payload shape
    dispatched = session.event_bus.last_event
    assert isinstance(dispatched, DummyTypeTextEvent)
    assert dispatched.node is element_obj
    assert dispatched.text == text
    assert dispatched.is_sensitive is False
    assert dispatched.sensitive_key_name is None


@pytest.mark.asyncio
async def test_email_detected_as_sensitive_round_116():
    server = BrowserUseServer(session_timeout_minutes=30)
    element_obj = object()
    session = FakeSession(element=element_obj)
    server.browser_session = session

    text = "alice@example.com"  # length >=6 and matches simple email heuristic
    result = await server._type_text(2, text)

    # Should indicate the email-sensitive branch
    assert result == 'Typed <email> into element 2'

    dispatched = session.event_bus.last_event
    assert isinstance(dispatched, DummyTypeTextEvent)
    assert dispatched.node is element_obj
    assert dispatched.text == text
    assert dispatched.is_sensitive is True
    assert dispatched.sensitive_key_name == 'email'


@pytest.mark.asyncio
async def test_credential_like_text_detected_as_sensitive_round_116():
    server = BrowserUseServer(session_timeout_minutes=30)
    element_obj = "node-cred"
    session = FakeSession(element=element_obj)
    server.browser_session = session

    # length >= 16, contains letters, digits, and '-' -> matches credential heuristic
    text = 'abcd1234-efgh5678'
    assert len(text) >= 16

    result = await server._type_text(3, text)

    assert result == 'Typed <credential> into element 3'

    dispatched = session.event_bus.last_event
    assert isinstance(dispatched, DummyTypeTextEvent)
    assert dispatched.node == element_obj
    assert dispatched.text == text
    assert dispatched.is_sensitive is True
    assert dispatched.sensitive_key_name == 'credential'
