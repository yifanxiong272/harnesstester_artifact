# file: sweagent/utils/log.py:57-90
# asked: {"lines": [63, 81, 82, 83, 84, 85, 86, 87, 89], "branches": [[62, 63], [80, 81], [82, 83], [82, 84], [84, 85], [84, 86], [86, 80], [86, 87], [88, 89]]}
# gained: {"lines": [63, 81, 82, 83, 84, 85, 86, 87, 89], "branches": [[62, 63], [80, 81], [82, 83], [82, 84], [84, 85], [84, 86], [86, 80], [86, 87], [88, 89]]}

import logging
import uuid
import contextlib
from types import SimpleNamespace

import pytest


def _make_dummy_rich_handler():
    # Create a lightweight dummy replacement for _RichHandlerWithEmoji
    class DummyHandler(logging.StreamHandler):
        def __init__(self, emoji=None, show_time=False, show_path=False):
            super().__init__()
            self.emoji = emoji
            self.show_time = show_time
            self.show_path = show_path

        # ensure setLevel exists
        def setLevel(self, level):
            super().setLevel(level)

    return DummyHandler


def test_get_logger_thread_name_additional_handlers_and_include(monkeypatch):
    # Import module under test
    import sweagent.utils.log as logmod

    # Prepare a unique logger base name to avoid collisions with other tests
    base_name = "testlogger_" + uuid.uuid4().hex

    # Monkeypatch environment to control internal behaviour and avoid side effects
    monkeypatch.setattr(logmod, "_THREAD_NAME_TO_LOG_SUFFIX", {}, raising=False)
    monkeypatch.setattr(logmod, "_SET_UP_LOGGERS", set(), raising=False)
    monkeypatch.setattr(logmod, "_STREAM_LEVEL", logging.DEBUG, raising=False)
    monkeypatch.setattr(logmod, "_LOG_LOCK", contextlib.nullcontext(), raising=False)
    # Provide the DummyHandler class so logmod can instantiate it
    monkeypatch.setattr(logmod, "_RichHandlerWithEmoji", _make_dummy_rich_handler(), raising=False)

    # Ensure logging.TRACE exists (some environments may not define it)
    monkeypatch.setattr(logging, "TRACE", 5, raising=False)

    # Force logger.hasHandlers() to return False so get_logger proceeds to set up handlers
    monkeypatch.setattr(logging.Logger, "hasHandlers", lambda self: False, raising=False)

    # Track calls to _add_logger_name_to_stream_handler
    called = []
    monkeypatch.setattr(logmod, "_add_logger_name_to_stream_handler", lambda logger: called.append(logger.name), raising=False)
    monkeypatch.setattr(logmod, "_INCLUDE_LOGGER_NAME_IN_STREAM_HANDLER", True, raising=False)

    # Replace threading.current_thread within the module to simulate a non-MainThread
    monkeypatch.setattr(logmod.threading, "current_thread", lambda: SimpleNamespace(name="Worker"), raising=False)

    # Build additional handlers with different my_filter behaviours:
    # - None -> should be added
    # - string that matches part of logger name -> should be added
    # - callable returning True -> should be added
    # - callable returning False -> should NOT be added
    handler_none = logging.NullHandler()
    handler_none.my_filter = None

    handler_str = logging.NullHandler()
    handler_str.my_filter = "Worker"  # will match the thread-suffixed name

    handler_callable_true = logging.NullHandler()
    handler_callable_true.my_filter = lambda name: True

    handler_callable_false = logging.NullHandler()
    handler_callable_false.my_filter = lambda name: False

    additional = {
        "none": handler_none,
        "str": handler_str,
        "callable_true": handler_callable_true,
        "callable_false": handler_callable_false,
    }
    monkeypatch.setattr(logmod, "_ADDITIONAL_HANDLERS", additional, raising=False)

    # Call the function under test
    expected_name = f"{base_name}-Worker"
    logger = logmod.get_logger(base_name, emoji=":smile:")

    # Postconditions / assertions:

    # Logger name should include the worker suffix (line 63 branch)
    assert logger.name == expected_name

    # The dummy rich handler should be present (it has attribute 'emoji')
    # plus the additional handlers that matched
    has_emoji_handler = any(hasattr(h, "emoji") for h in logger.handlers)
    assert has_emoji_handler, "expected a rich handler instance with 'emoji' attribute"

    # Check that the handlers that should have been added are in logger.handlers
    assert handler_none in logger.handlers, "handler with my_filter=None should be added"
    assert handler_str in logger.handlers, "handler with my_filter=str matching name should be added"
    assert handler_callable_true in logger.handlers, "handler with my_filter callable returning True should be added"
    assert handler_callable_false not in logger.handlers, "handler with my_filter callable returning False should NOT be added"

    # _add_logger_name_to_stream_handler should have been called because _INCLUDE_LOGGER_NAME_IN_STREAM_HANDLER=True
    assert called == [logger.name]

    # Clean up: remove handlers from the logger to avoid polluting global logging state
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.propagate = True

    # Also remove from the module's _SET_UP_LOGGERS if present
    if hasattr(logmod, "_SET_UP_LOGGERS"):
        s = getattr(logmod, "_SET_UP_LOGGERS")
        if isinstance(s, set) and logger.name in s:
            s.discard(logger.name)
