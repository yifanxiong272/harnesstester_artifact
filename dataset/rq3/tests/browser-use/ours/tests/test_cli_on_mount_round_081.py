import types
import pytest

import importlib

# Import the module under test
import browser_use.cli as cli


class DummyTelemetry:
    def __init__(self):
        self.captured = []

    def capture(self, event):
        # store the event object for inspection
        self.captured.append(event)


class DummyCLITelemetryEvent:
    def __init__(self, *, version=None, action=None, mode=None, model=None, model_provider=None):
        self.version = version
        self.action = action
        self.mode = mode
        self.model = model
        self.model_provider = model_provider


def make_dummy_self(**kwargs):
    """Create a simple namespace object with default no-op attributes for on_mount."""
    ns = types.SimpleNamespace()
    # Default no-op methods/attributes
    ns.setup_richlog_logging = kwargs.get('setup_richlog_logging', lambda: None)
    ns.task_history = kwargs.get('task_history', None)
    ns.setup_cdp_logger = kwargs.get('setup_cdp_logger', lambda: None)
    ns.browser_session = kwargs.get('browser_session', False)
    ns.setup_event_bus_listener = kwargs.get('setup_event_bus_listener', lambda: None)
    ns._telemetry = kwargs.get('_telemetry', DummyTelemetry())
    ns.llm = kwargs.get('llm', None)

    # query_one should accept (selector, cls) and return an object with focus()
    ns.query_one = kwargs.get('query_one', lambda selector, cls: types.SimpleNamespace(focus=lambda: None))
    return ns


def test_on_mount_success_history_and_cdp_and_telemetry_round_081(monkeypatch):
    # Arrange: patch module-level dependencies
    monkeypatch.setattr(cli, 'READLINE_AVAILABLE', True)

    added = []

    def _add_history(item):
        added.append(item)

    monkeypatch.setattr(cli, '_add_history', _add_history)

    # Patch telemetry event class and version function
    monkeypatch.setattr(cli, 'CLITelemetryEvent', DummyCLITelemetryEvent)
    monkeypatch.setattr(cli, 'get_browser_use_version', lambda: '1.2.3')

    # Prepare dummy self with history, llm and query_one returning focusable object
    focused = {'called': False}

    def query_one(sel, cls):
        def focus():
            focused['called'] = True

        return types.SimpleNamespace(focus=focus)

    dummy_telemetry = DummyTelemetry()
    dummy_self = make_dummy_self(
        setup_richlog_logging=lambda: None,
        task_history=['x', 'y'],
        setup_cdp_logger=lambda: setattr(dummy_self, 'cdp_setup', True) if 'dummy_self' in globals() else None,
        browser_session=True,
        setup_event_bus_listener=lambda: setattr(dummy_self, 'event_listener_set', True) if 'dummy_self' in globals() else None,
        _telemetry=dummy_telemetry,
        llm=types.SimpleNamespace(model='m1', provider='p1'),
        query_one=query_one,
    )

    # A little trick: the lambdas above reference dummy_self; ensure attribute setting works
    # Replace setup_cdp_logger and setup_event_bus_listener now that dummy_self exists
    dummy_self.setup_cdp_logger = lambda: setattr(dummy_self, 'cdp_setup', True)
    dummy_self.setup_event_bus_listener = lambda: setattr(dummy_self, 'event_listener_set', True)

    # Act
    cli.BrowserUseApp.on_mount(dummy_self)

    # Assert: history items added
    assert added == ['x', 'y']
    # Input focused
    assert focused['called'] is True
    # CDP logger and event listener were set
    assert getattr(dummy_self, 'cdp_setup', False) is True
    assert getattr(dummy_self, 'event_listener_set', False) is True
    # Telemetry captured exactly one event and fields set
    assert len(dummy_telemetry.captured) == 1
    ev = dummy_telemetry.captured[0]
    assert isinstance(ev, DummyCLITelemetryEvent)
    assert ev.version == '1.2.3'
    assert ev.action == 'start'
    assert ev.mode == 'interactive'
    assert ev.model == 'm1'
    assert ev.model_provider == 'p1'


def test_on_mount_no_history_and_no_browser_session_round_081(monkeypatch):
    # Arrange: history not available path
    monkeypatch.setattr(cli, 'READLINE_AVAILABLE', False)
    # Ensure _add_history exists but shouldn't be used
    called = {'used': False}

    def _add_history(item):
        called['used'] = True

    monkeypatch.setattr(cli, '_add_history', _add_history)

    # Patch telemetry event class and version function
    monkeypatch.setattr(cli, 'CLITelemetryEvent', DummyCLITelemetryEvent)
    monkeypatch.setattr(cli, 'get_browser_use_version', lambda: '9.9.9')

    # Prepare dummy self with no llm and no browser session
    dummy_telemetry = DummyTelemetry()
    dummy_self = make_dummy_self(
        setup_richlog_logging=lambda: None,
        task_history=None,
        setup_cdp_logger=lambda: setattr(dummy_self, 'cdp_setup', True) if 'dummy_self' in globals() else None,
        browser_session=False,
        setup_event_bus_listener=lambda: setattr(dummy_self, 'event_listener_set', True) if 'dummy_self' in globals() else None,
        _telemetry=dummy_telemetry,
        llm=None,
        query_one=lambda s, c: types.SimpleNamespace(focus=lambda: None),
    )

    dummy_self.setup_cdp_logger = lambda: setattr(dummy_self, 'cdp_setup', True)
    dummy_self.setup_event_bus_listener = lambda: setattr(dummy_self, 'event_listener_set', True)

    # Act
    cli.BrowserUseApp.on_mount(dummy_self)

    # Assert: _add_history not used
    assert called['used'] is False
    # CDP setup was called but event listener not called because browser_session is False
    assert getattr(dummy_self, 'cdp_setup', False) is True
    assert getattr(dummy_self, 'event_listener_set', False) is False
    # Telemetry captured and model/provider are None
    assert len(dummy_telemetry.captured) == 1
    ev = dummy_telemetry.captured[0]
    assert isinstance(ev, DummyCLITelemetryEvent)
    assert ev.version == '9.9.9'
    assert ev.model is None
    assert ev.model_provider is None


def test_on_mount_richlog_setup_failure_raises_runtime_error_round_081(monkeypatch):
    # Arrange: Make setup_richlog_logging raise to exercise the exception -> RuntimeError path
    def raise_setup():
        raise Exception('boom')

    dummy_self = make_dummy_self(setup_richlog_logging=raise_setup)

    # Act / Assert
    with pytest.raises(RuntimeError) as excinfo:
        cli.BrowserUseApp.on_mount(dummy_self)

    assert 'Failed to set up RichLog logging' in str(excinfo.value)


def test_on_mount_focus_input_raises_logs_but_continues_round_081(monkeypatch):
    # Arrange: focus raises, but other non-critical steps continue
    monkeypatch.setattr(cli, 'READLINE_AVAILABLE', False)
    monkeypatch.setattr(cli, 'CLITelemetryEvent', DummyCLITelemetryEvent)
    monkeypatch.setattr(cli, 'get_browser_use_version', lambda: '0.0.0')

    def query_one(sel, cls):
        def focus():
            raise RuntimeError('focus fail')

        return types.SimpleNamespace(focus=focus)

    dummy_telemetry = DummyTelemetry()
    dummy_self = make_dummy_self(
        setup_richlog_logging=lambda: None,
        task_history=None,
        setup_cdp_logger=lambda: setattr(dummy_self, 'cdp_setup', True) if 'dummy_self' in globals() else None,
        browser_session=True,
        setup_event_bus_listener=lambda: setattr(dummy_self, 'event_listener_set', True) if 'dummy_self' in globals() else None,
        _telemetry=dummy_telemetry,
        llm=None,
        query_one=query_one,
    )

    dummy_self.setup_cdp_logger = lambda: setattr(dummy_self, 'cdp_setup', True)
    dummy_self.setup_event_bus_listener = lambda: setattr(dummy_self, 'event_listener_set', True)

    # Act: should not raise despite focus() raising
    cli.BrowserUseApp.on_mount(dummy_self)

    # Assert: CDP and event listener still set and telemetry still captured
    assert getattr(dummy_self, 'cdp_setup', False) is True
    assert getattr(dummy_self, 'event_listener_set', False) is True
    assert len(dummy_telemetry.captured) == 1
    ev = dummy_telemetry.captured[0]
    assert ev.version == '0.0.0'
    assert ev.action == 'start'
