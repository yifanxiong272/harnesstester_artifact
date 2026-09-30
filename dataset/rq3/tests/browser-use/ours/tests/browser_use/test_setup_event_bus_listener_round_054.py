import logging
import types
from browser_use.cli import BrowserUseApp


class FakeEventsLog:
    def __init__(self):
        self.writes = []

    def write(self, s: str):
        # deterministic append
        self.writes.append(s)


class FakeEventBus:
    def __init__(self, handlers=None):
        # handlers is a dict: event_type -> list of handlers
        self.handlers = handlers if handlers is not None else {}
        self.on_calls = []

    def on(self, pattern, handler):
        # record registration calls
        self.on_calls.append((pattern, handler))


class HandlersThatRaise:
    # Provide an items() that raises to simulate cleanup exception
    def items(self):
        raise RuntimeError("handlers access failure")


def make_app_instance():
    # Create an instance without running __init__ to avoid heavy setup
    app = object.__new__(BrowserUseApp)
    # Ensure fields expected by setup_event_bus_listener exist
    app._event_bus_handler_func = None
    app._event_bus_handler_id = None
    return app


def test_no_browser_session_round_054():
    """If browser_session is falsy, setup_event_bus_listener should return early
    and not set an event handler."""
    app = make_app_instance()
    app.browser_session = None

    # Provide a benign query_one (should not be called)
    app.query_one = lambda selector, cls=None: None

    # Call the target method
    BrowserUseApp.setup_event_bus_listener(app)

    # Since there is no browser_session, no handler should be set
    assert app._event_bus_handler_func is None
    assert app._event_bus_handler_id is None


def test_cleanup_and_register_round_054():
    """When an old handler exists and event bus has handlers, it should be removed,
    then a new handler must be registered and stored. Also exercise the created
    log_event with an event that has model_dump and long content to trigger truncation."""
    app = make_app_instance()

    # Create a sentinel old handler to be removed
    def old_handler(ev):
        pass

    # Setup event bus with a handler list containing the sentinel
    handlers = {'click': [old_handler, lambda e: None], 'hover': []}
    event_bus = FakeEventBus(handlers=handlers)
    app.browser_session = types.SimpleNamespace(event_bus=event_bus)

    fake_log = FakeEventsLog()
    app.query_one = lambda selector, cls=None: fake_log

    # Pre-set an existing handler function so cleanup code runs
    app._event_bus_handler_func = old_handler
    app._event_bus_handler_id = 12345

    # Run
    BrowserUseApp.setup_event_bus_listener(app)

    # Old handler removed from all lists
    for lst in handlers.values():
        assert old_handler not in lst

    # A new handler function was stored
    assert callable(app._event_bus_handler_func)
    assert app._event_bus_handler_id == id(app._event_bus_handler_func)

    # The event bus on() was called to register wildcard handler
    assert len(event_bus.on_calls) == 1
    pattern, registered = event_bus.on_calls[0]
    assert pattern == '*'
    # The registered handler should be the same callable stored on app
    assert registered is app._event_bus_handler_func

    # Now exercise the log_event path: create an event with model_dump
    class EventWithDump:
        def model_dump(self, exclude_unset=True):
            # Create a dict that will stringify to a long string > 200 chars
            return {
                'screenshot': b'\x00' * 10,
                'dom_state': '<full dom>' * 20,
                'long_field': 'x' * 300,
            }

    ev = EventWithDump()

    # Call the registered handler (log_event)
    app._event_bus_handler_func(ev)

    # The events log should have a single write with truncated content
    assert len(fake_log.writes) == 1
    written = fake_log.writes[0]

    # It must include the arrow and the event class name
    assert '\u2192' in written
    assert 'EventWithDump' in written

    # The event string portion must be truncated to 200 chars plus '...'
    # Extract content after the closing color tag '[/] '
    marker = '[/] '
    assert marker in written
    event_str = written.split(marker, 1)[1]
    assert len(event_str) <= 203  # 200 chars + '...'
    if len(event_str) == 203:
        assert event_str.endswith('...')


def test_query_one_raises_after_cleanup_round_054():
    """If query_one raises after cleanup, setup_event_bus_listener should return
    and the stored handler vars should be reset to None."""
    app = make_app_instance()

    # Create an old handler that will be attempted to be removed
    def old_handler(ev):
        pass

    # Make handlers normal so removal works
    handlers = {'click': [old_handler]}
    event_bus = FakeEventBus(handlers=handlers)
    app.browser_session = types.SimpleNamespace(event_bus=event_bus)

    app._event_bus_handler_func = old_handler
    app._event_bus_handler_id = 999

    # Make query_one raise to simulate widget not ready
    def raising_query(selector, cls=None):
        raise RuntimeError('widget missing')

    app.query_one = raising_query

    BrowserUseApp.setup_event_bus_listener(app)

    # After exception during widget retrieval, the _event_bus_handler_func should have been cleared
    assert app._event_bus_handler_func is None
    assert app._event_bus_handler_id is None


def test_log_event_no_model_dump_and_format_exception_round_054():
    """Exercise the branches where event has no model_dump (falls back to str(event)),
    and where model_dump raises causing the formatting-exception branch."""
    app = make_app_instance()

    event_bus = FakeEventBus(handlers={})
    app.browser_session = types.SimpleNamespace(event_bus=event_bus)

    fake_log = FakeEventsLog()
    app.query_one = lambda selector, cls=None: fake_log

    # Ensure no previous handler
    app._event_bus_handler_func = None
    app._event_bus_handler_id = None

    # Register handler by running setup
    BrowserUseApp.setup_event_bus_listener(app)

    # 1) Event without model_dump -> str(event) used
    class SimpleEvent:
        def __repr__(self):
            return '<SimpleEvent repr>'

    app._event_bus_handler_func(SimpleEvent())
    assert any('SimpleEvent' in s or '<SimpleEvent repr>' in s for s in fake_log.writes)

    # Clear writes
    fake_log.writes.clear()

    # 2) Event whose model_dump raises an exception -> should write error-formatted message
    class BadEvent:
        def model_dump(self, exclude_unset=True):
            raise ValueError('dump failed')

    app._event_bus_handler_func(BadEvent())
    assert len(fake_log.writes) == 1
    last = fake_log.writes[-1]
    # Should include error formatting marker and the class name
    assert '(error formatting' in last or 'error formatting' in last
    assert 'BadEvent' in last
