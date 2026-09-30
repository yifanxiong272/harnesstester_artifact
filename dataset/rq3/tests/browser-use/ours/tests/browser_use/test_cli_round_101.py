import logging
import types
import pytest

import browser_use.cli as cli


class DummyRichLog:
    def __init__(self):
        self.messages = []

    def write(self, msg):
        # Record messages so tests can assert on them
        self.messages.append(msg)


class DummyApp:
    def __init__(self, rich_log):
        self._rich_log = rich_log

    def query_one(self, selector, rich_log_type=None):
        # Accept the selector and type arg and return our dummy rich log
        assert selector == '#cdp-log'
        # rich_log_type may be the original RichLog symbol; we ignore it
        return self._rich_log


LOGGER_NAMES = [
    'websockets.client',
    'cdp_use',
    'cdp_use.client',
    'cdp_use.cdp',
    'cdp_use.cdp.registry',
]


def _clear_and_prepare_loggers():
    # Save original handlers so we can restore after test
    original = {}
    for name in LOGGER_NAMES:
        logger = logging.getLogger(name)
        original[name] = list(logger.handlers)
        # Remove handlers to avoid interference and ensure deterministic ordering
        for h in list(logger.handlers):
            logger.removeHandler(h)
        # Ensure logger will emit all levels during tests
        logger.setLevel(logging.DEBUG)
    return original


def _restore_loggers(original):
    for name, handlers in original.items():
        logger = logging.getLogger(name)
        # Remove any handlers added during the test
        for h in list(logger.handlers):
            logger.removeHandler(h)
        # Restore original handlers
        for h in handlers:
            logger.addHandler(h)


def test_setup_cdp_logger_writes_levels_and_truncates_round_101():
    # Replace the module RichLog symbol with our dummy so the code path resolves
    original_richlog = getattr(cli, 'RichLog', None)
    cli.RichLog = DummyRichLog

    rich_log = DummyRichLog()
    app = DummyApp(rich_log)

    original_handlers = _clear_and_prepare_loggers()
    try:
        # Call the method under test on our dummy app instance
        cli.BrowserUseApp.setup_cdp_logger(app)

        # Use the 'cdp_use' logger to emit messages at various levels
        logger = logging.getLogger('cdp_use')
        logger.setLevel(logging.DEBUG)

        logger.info('short-info')
        logger.warning('warn-msg')
        logger.error('error-msg')

        # Emit a very long message to force truncation (>300 chars)
        long_msg = 'x' * 400
        logger.info(long_msg)

        # Assertions: check that the DummyRichLog captured color-coded messages
        # There should be at least 4 messages recorded
        assert len(rich_log.messages) >= 4

        # First INFO -> cyan
        assert any(m.startswith('[cyan]short-info') for m in rich_log.messages), (
            'Expected cyan-wrapped short-info in messages: %r' % rich_log.messages
        )
        # WARNING -> yellow
        assert any(m.startswith('[yellow]warn-msg') for m in rich_log.messages), (
            'Expected yellow-wrapped warn-msg in messages: %r' % rich_log.messages
        )
        # ERROR -> red
        assert any(m.startswith('[red]error-msg') for m in rich_log.messages), (
            'Expected red-wrapped error-msg in messages: %r' % rich_log.messages
        )

        # Long message should be truncated to 300 chars + '...' and wrapped in cyan for INFO
        truncated_candidates = [m for m in rich_log.messages if m.startswith('[cyan]') and m.endswith('...[/]')]
        assert truncated_candidates, 'Expected a truncated cyan message ending with ...[/]; got: %r' % rich_log.messages

        # Check truncation size inside (strip tags and closing) -> ensure inner content ends with '...'
        # (We already checked endswith '...[/]') - also verify the truncated part length is 300 + '...'
        candidate = truncated_candidates[-1]
        # strip prefix '[cyan]' and suffix '[/]'
        inner = candidate[len('[cyan]'):-len('[/]')]
        assert inner.endswith('...')
        assert len(inner) == 303

    finally:
        # Cleanup: restore module symbol and logger handlers
        if original_richlog is None:
            delattr(cli, 'RichLog')
        else:
            cli.RichLog = original_richlog
        _restore_loggers(original_handlers)


def test_setup_cdp_logger_handles_write_exception_round_101():
    # Ensure RichLog symbol is present
    original_richlog = getattr(cli, 'RichLog', None)
    cli.RichLog = DummyRichLog

    rich_log = DummyRichLog()
    app = DummyApp(rich_log)

    original_handlers = _clear_and_prepare_loggers()
    try:
        # Setup the handler
        cli.BrowserUseApp.setup_cdp_logger(app)
        logger = logging.getLogger('cdp_use')
        logger.setLevel(logging.DEBUG)

        # Find the handler that the setup added (it should have a reference to our rich_log)
        handlers = [h for h in logger.handlers if hasattr(h, 'rich_log')]
        assert handlers, 'No handler with rich_log found on logger.handlers'
        handler = handlers[0]

        # Replace the write method to raise to exercise the exception path
        def raising_write(msg):
            raise RuntimeError('boom')

        handler.rich_log.write = raising_write

        # Replace handler.handleError with a recorder so we can assert it was called
        called = {'hit': False}

        def recorder(self, record):
            # mark that handleError was invoked
            called['hit'] = True

        handler.handleError = types.MethodType(recorder, handler)

        # Emit a message that will hit the handler and cause write() to raise
        logger.info('trigger-exception')

        assert called['hit'] is True, 'Expected handler.handleError to be invoked when write() raises'

    finally:
        if original_richlog is None:
            delattr(cli, 'RichLog')
        else:
            cli.RichLog = original_richlog
        _restore_loggers(original_handlers)
