# file: browser_use/cli.py:618-703
# asked: {"lines": [618, 621, 622, 623, 624, 627, 630, 631, 633, 634, 637, 640, 641, 642, 644, 647, 650, 651, 654, 655, 656, 657, 659, 662, 663, 664, 665, 669, 670, 671, 672, 673, 676, 677, 678, 679, 680, 681, 684, 700, 701, 702, 703], "branches": [[640, 641], [640, 644], [654, 655], [654, 656], [656, 657], [656, 659], [669, 670], [669, 676], [676, 677], [676, 684], [677, 676], [677, 678], [678, 676], [678, 679], [684, 0], [684, 700]]}
# gained: {"lines": [618, 621, 622, 623, 624, 627, 630, 631, 633, 634, 640, 641, 642, 644, 647, 650, 651, 654, 655, 656, 657, 659, 662, 663, 664, 665, 669, 670, 671, 672, 673, 676, 677, 678, 679, 680, 681, 684, 700, 701, 702, 703], "branches": [[640, 641], [640, 644], [654, 655], [654, 656], [656, 657], [656, 659], [669, 670], [669, 676], [676, 677], [676, 684], [677, 676], [677, 678], [678, 679], [684, 0], [684, 700]]}

import importlib
import logging
import os
import types

import pytest


def _backup_loggers(names):
    bak = {}
    for name in names:
        logger = logging.getLogger(name)
        bak[name] = {
            "handlers": list(logger.handlers),
            "propagate": logger.propagate,
            "level": logger.level,
        }
    # also backup root
    root = logging.getLogger()
    bak["ROOT"] = {"handlers": list(root.handlers), "level": root.level}
    return bak


def _restore_loggers(bak):
    for name, state in bak.items():
        if name == "ROOT":
            root = logging.getLogger()
            root.handlers = list(state["handlers"])
            root.setLevel(state["level"])
            continue
        logger = logging.getLogger(name)
        logger.handlers = list(state["handlers"])
        logger.propagate = state["propagate"]
        logger.setLevel(state["level"])


class FakeRichLogWidget:
    pass


def make_fake_handler_class(calls_list):
    class FakeHandler(logging.Handler):
        def __init__(self, widget):
            super().__init__()
            self.widget = widget
            self.level_set = None
            self.fmt = None
            calls_list.append(("init", widget))

        def emit(self, record):
            # no-op; record events can be appended if needed
            calls_list.append(("emit", record))

        def setLevel(self, level):
            # record the call and then call base class to keep internal state consistent
            self.level_set = level
            super().setLevel(level)
            calls_list.append(("setLevel", level))

        def setFormatter(self, fmt):
            self.fmt = fmt
            super().setFormatter(fmt)
            calls_list.append(("setFormatter", fmt))

    return FakeHandler


def _ensure_agent_logger_exists():
    # create a logger whose name includes 'browser_use.Agent' to exercise that branch
    logging.getLogger("browser_use.Agent.42")


@pytest.mark.parametrize("env_value, expected_level, expected_fmt", [
    ("result", 35, "%(message)s"),
    ("debug", logging.DEBUG, "%(levelname)-8s [%(name)s] %(message)s"),
    ("info", logging.INFO, "%(levelname)-8s [%(name)s] %(message)s"),
])
def test_setup_richlog_logging_various_levels(monkeypatch, env_value, expected_level, expected_fmt):
    # Import module under test
    module = importlib.import_module("browser_use.cli")

    # Prepare backup of potentially touched loggers
    # list includes the ones the function will touch
    all_logger_names = [
        "browser_use",
        "browser_use.Agent",
        "browser_use.controller",
        "browser_use.agent",
        "browser_use.agent.service",
        # include third party list from code
        "WDM",
        "httpx",
        "selenium",
        "playwright",
        "urllib3",
        "asyncio",
        "openai",
        "httpcore",
        "charset_normalizer",
        "anthropic._base_client",
        "PIL.PngImagePlugin",
        "trafilatura.htmlprocessing",
        "trafilatura",
        "groq",
    ]
    # Ensure the dynamic agent logger exists for the loop that checks Logger.manager.loggerDict
    _ensure_agent_logger_exists()
    # include that dynamic logger name
    all_logger_names.append("browser_use.Agent.42")

    bak = _backup_loggers(all_logger_names)

    try:
        # Create a fake handler class that is a proper logging.Handler subclass
        calls = []
        FakeHandler = make_fake_handler_class(calls)

        # Monkeypatch the RichLogHandler in the module to our fake
        monkeypatch.setattr(module, "RichLogHandler", FakeHandler)

        # Monkeypatch addLoggingLevel to add mapping for RESULT when needed.
        def fake_addLoggingLevel(name, level):
            # emulate behavior of adding a new level
            logging.addLevelName(level, name)
            # ensure name->level mapping also exists
            logging._nameToLevel[name] = level

        monkeypatch.setattr(module, "addLoggingLevel", fake_addLoggingLevel)

        # Prepare a fake self with query_one method
        fake_widget = FakeRichLogWidget()
        fake_self = types.SimpleNamespace()
        fake_self.query_one = lambda selector, cls: fake_widget

        # Set environment variable as required
        monkeypatch.setenv("BROWSER_USE_LOGGING_LEVEL", env_value)

        # Call the method under test
        module.BrowserUseApp.setup_richlog_logging(fake_self)

        # Assertions:
        # The root logger level should match expected
        root = logging.getLogger()
        if env_value == "result":
            # RESULT numeric value is 35
            assert root.level == expected_level
        else:
            assert root.level == expected_level

        # The fake handler should have been added to root.handlers
        assert any(isinstance(h, FakeHandler) for h in root.handlers)

        # The browser_use logger should have our handler and not propagate
        browser_logger = logging.getLogger("browser_use")
        assert browser_logger.propagate is False
        assert any(isinstance(h, FakeHandler) for h in browser_logger.handlers)
        assert browser_logger.level == root.level

        # The dynamic agent logger created earlier should have been adjusted
        dyn_logger = logging.getLogger("browser_use.Agent.42")
        assert dyn_logger.propagate is False
        assert any(isinstance(h, FakeHandler) for h in dyn_logger.handlers)
        assert dyn_logger.level == root.level

        # Third-party logger example should be set to ERROR and get our handler
        third = logging.getLogger("httpx")
        assert third.level == logging.ERROR
        assert third.propagate is False
        assert any(isinstance(h, FakeHandler) for h in third.handlers)

        # Check that the fake handler got the formatter with expected format string
        # Find the fake handler instance
        fh = next(h for h in root.handlers if isinstance(h, FakeHandler))
        assert hasattr(fh, "fmt")
        # The formatter object stored should expose _fmt (logging.Formatter)
        assert getattr(fh.fmt, "_fmt") == expected_fmt

    finally:
        # Cleanup: remove RESULTS level name if we added it
        logging._nameToLevel.pop("RESULT", None)
        logging._levelToName.pop(35, None)
        # Restore loggers to original state to avoid test interference
        _restore_loggers(bak)


def test_setup_richlog_logging_addlogging_raises_attributeerror(monkeypatch):
    """
    Verify that if addLoggingLevel raises AttributeError, the function still proceeds.
    Also exercise the non-result formatter branch by setting env to 'other'.
    """
    module = importlib.import_module("browser_use.cli")

    # Backup relevant loggers
    all_logger_names = [
        "browser_use",
        "browser_use.Agent",
        "browser_use.controller",
        "browser_use.agent",
        "browser_use.agent.service",
        "browser_use.Agent.99",
        "httpx",
    ]
    _ensure_agent_logger_exists()
    bak = _backup_loggers(all_logger_names)

    try:
        calls = []
        FakeHandler = make_fake_handler_class(calls)
        monkeypatch.setattr(module, "RichLogHandler", FakeHandler)

        # Simulate addLoggingLevel raising AttributeError (level already exists)
        def raising_addLoggingLevel(name, level):
            raise AttributeError("already exists")

        monkeypatch.setattr(module, "addLoggingLevel", raising_addLoggingLevel)

        fake_widget = FakeRichLogWidget()
        fake_self = types.SimpleNamespace()
        fake_self.query_one = lambda selector, cls: fake_widget

        monkeypatch.setenv("BROWSER_USE_LOGGING_LEVEL", "other")  # exercise else branch
        module.BrowserUseApp.setup_richlog_logging(fake_self)

        # Validate root level became INFO since not result or debug
        root = logging.getLogger()
        assert root.level == logging.INFO

        # Browser logger uses our handler
        browser_logger = logging.getLogger("browser_use")
        assert any(isinstance(h, FakeHandler) for h in browser_logger.handlers)
        assert browser_logger.propagate is False

        # Third party logger check
        third = logging.getLogger("httpx")
        assert third.level == logging.ERROR
        assert any(isinstance(h, FakeHandler) for h in third.handlers)

    finally:
        _restore_loggers(bak)
