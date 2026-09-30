import logging
import os
import types
import importlib
import inspect
import pytest

import browser_use.cli as cli


class DummyRich:
    def __init__(self):
        self.written = []

    def write(self, msg):
        # emulate RichLog widget write method
        self.written.append(msg)


class DummySelf:
    def __init__(self, rich):
        self._rich = rich

    def query_one(self, selector, cls):
        # BrowserUseApp.setup_richlog_logging expects to call query_one with '#main-output-log'
        assert selector == '#main-output-log'
        return self._rich


def _safe_restore_logger_state(saved):
    root = logging.getLogger()
    root.handlers = saved['root_handlers']
    root.setLevel(saved['root_level'])
    # restore any modified third-party loggers and browser_use logger
    for name, meta in saved['loggers'].items():
        lg = logging.getLogger(name)
        lg.setLevel(meta['level'])
        lg.propagate = meta['propagate']
        lg.handlers = meta['handlers']


def _snapshot_logger_state(names_to_snapshot):
    root = logging.getLogger()
    saved = {
        'root_handlers': list(root.handlers),
        'root_level': root.level,
        'loggers': {}
    }
    for name in names_to_snapshot:
        lg = logging.getLogger(name)
        saved['loggers'][name] = {
            'level': lg.level,
            'propagate': lg.propagate,
            'handlers': list(lg.handlers),
        }
    return saved


def test_setup_richlog_logging_result_round_048(monkeypatch):
    """Ensure 'result' branch registers RESULT level, sets handler and propagates to browser_use loggers."""
    # Prepare environment
    monkeypatch.setenv('BROWSER_USE_LOGGING_LEVEL', 'result')

    # Ensure addLoggingLevel registers a numeric level name 'RESULT' so setLevel('RESULT') works
    def mock_add_logging_level(name, value):
        # Register name->value mapping similar to real implementation
        logging.addLevelName(value, name)
        # ensure reverse map also contains it
        try:
            logging._nameToLevel[name] = value
        except Exception:
            # be resilient across logging internals
            pass

    monkeypatch.setattr(cli, 'addLoggingLevel', mock_add_logging_level)

    rich = DummyRich()
    self = DummySelf(rich)

    # snapshot state to restore later
    names = ['browser_use', 'browser_use.Agent', 'httpx']
    saved = _snapshot_logger_state(names)

    # Add a dynamic agent logger into Logger.manager.loggerDict to hit loop branch
    # Creating the logger via logging.getLogger ensures it's a real logging.Logger
    dynamic_logger_name = 'browser_use.Agent.dynamic_task'
    dynamic_logger = logging.getLogger(dynamic_logger_name)
    # ensure presence in manager dict explicitly (getLogger already does this)
    logging.Logger.manager.loggerDict[dynamic_logger_name] = dynamic_logger

    try:
        # call the target function as an unbound function with our fake self
        cli.BrowserUseApp.setup_richlog_logging(self)

        root = logging.getLogger()
        # Check root has our RichLogHandler instance
        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert isinstance(handler, cli.RichLogHandler)

        # RESULT was registered to numeric value 35 in project original code; check root.level is set
        # We verify it's an integer and corresponds to a level name 'RESULT'
        assert isinstance(root.level, int)
        assert logging.getLevelName(root.level) == 'RESULT'

        # browser_use logger should be configured
        browser_logger = logging.getLogger('browser_use')
        assert browser_logger.propagate is False
        assert browser_logger.handlers == [handler]
        assert browser_logger.level == root.level

        # dynamic agent logger from loggerDict should have been configured
        agent_logger = logging.getLogger(dynamic_logger_name)
        assert agent_logger.propagate is False
        assert agent_logger.handlers == [handler]
        assert agent_logger.level == root.level

        # third-party logger should be set to ERROR and use our handler
        tp = logging.getLogger('httpx')
        assert tp.level == logging.ERROR
        assert tp.propagate is False
        # handlers should be replaced with our handler
        assert tp.handlers == [handler]

    finally:
        # cleanup: remove dynamic logger entry and restore state
        if dynamic_logger_name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[dynamic_logger_name]
        _safe_restore_logger_state(saved)


def test_setup_richlog_logging_debug_round_048(monkeypatch):
    """When BROWSER_USE_LOGGING_LEVEL=debug, root level becomes DEBUG and formatter uses verbose pattern."""
    monkeypatch.setenv('BROWSER_USE_LOGGING_LEVEL', 'debug')

    # Make addLoggingLevel raise an AttributeError to hit the except path
    def raising_add_logging_level(*a, **kw):
        raise AttributeError('already exists')

    monkeypatch.setattr(cli, 'addLoggingLevel', raising_add_logging_level)

    rich = DummyRich()
    self = DummySelf(rich)

    names = ['browser_use', 'openai']
    saved = _snapshot_logger_state(names)

    try:
        cli.BrowserUseApp.setup_richlog_logging(self)

        root = logging.getLogger()
        # root level should be logging.DEBUG
        assert root.level == logging.DEBUG

        handler = root.handlers[0]
        # The formatter should be set to the verbose format for non-'result' path
        fmt = handler.formatter._fmt
        assert '%(levelname)-8s [%(name)s] %(message)s' in fmt

        # Ensure some third-party logger configured to ERROR
        tp = logging.getLogger('openai')
        assert tp.level == logging.ERROR
        assert tp.propagate is False
        assert tp.handlers == [handler]

    finally:
        _safe_restore_logger_state(saved)


def test_setup_richlog_logging_info_round_048(monkeypatch):
    """When BROWSER_USE_LOGGING_LEVEL is neither 'result' nor 'debug', INFO branch is taken."""
    monkeypatch.setenv('BROWSER_USE_LOGGING_LEVEL', 'info')

    # Simulate addLoggingLevel raising so code path swallows it and proceeds
    monkeypatch.setattr(cli, 'addLoggingLevel', lambda *a, **k: (_ for _ in ()).throw(AttributeError('exists')))

    rich = DummyRich()
    self = DummySelf(rich)

    names = ['browser_use', 'PIL.PngImagePlugin']
    saved = _snapshot_logger_state(names)

    try:
        cli.BrowserUseApp.setup_richlog_logging(self)

        root = logging.getLogger()
        assert root.level == logging.INFO

        handler = root.handlers[0]
        # Handler should be our RichLogHandler and formatter in verbose mode
        assert isinstance(handler, cli.RichLogHandler)
        assert handler.formatter._fmt == '%(levelname)-8s [%(name)s] %(message)s'

        tp = logging.getLogger('PIL.PngImagePlugin')
        assert tp.level == logging.ERROR
        assert tp.propagate is False
        assert tp.handlers == [handler]

    finally:
        _safe_restore_logger_state(saved)
