# file: sweagent/utils/log.py:160-175
# asked: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175], "branches": [[169, 0], [169, 170], [171, 169], [171, 172], [172, 171], [172, 173], [174, 171], [174, 175]]}
# gained: {"lines": [167, 168, 169, 170, 171, 172, 173, 174, 175], "branches": [[169, 0], [169, 170], [171, 169], [171, 172], [172, 171], [172, 173], [174, 171], [174, 175]]}

import logging
import types
import pytest

from sweagent.utils import log as log_module


class DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyRichHandler:
    def __init__(self, level):
        self.level = level
        self.set_calls = []

    def setLevel(self, lvl):
        self.set_calls.append(lvl)
        self.level = lvl


def _cleanup_loggers(names):
    for name in names:
        logger = logging.getLogger(name)
        logger.handlers[:] = []


def test_set_stream_handler_levels_sets_level_when_lower(monkeypatch):
    # Prepare module globals
    monkeypatch.setattr(log_module, "_RichHandlerWithEmoji", DummyRichHandler, raising=False)
    monkeypatch.setattr(log_module, "_LOG_LOCK", DummyLock(), raising=False)
    monkeypatch.setattr(log_module, "_SET_UP_LOGGERS", ["test.logger.one"], raising=False)

    logger_name = "test.logger.one"
    logger = logging.getLogger(logger_name)
    # Ensure clean handlers list before test
    logger.handlers[:] = []

    try:
        # Handler with lower current level (numerically smaller)
        handler = DummyRichHandler(level=10)
        logger.handlers.append(handler)

        # Call function to set stream level to 20 (should call handler.setLevel)
        log_module.set_stream_handler_levels(20)

        # _STREAM_LEVEL should be updated
        assert getattr(log_module, "_STREAM_LEVEL") == 20

        # Handler's setLevel should have been called and level updated
        assert handler.set_calls == [20]
        assert handler.level == 20
    finally:
        # Cleanup handlers to avoid state pollution
        _cleanup_loggers([logger_name])


def test_set_stream_handler_levels_does_not_lower_existing_higher_level(monkeypatch):
    # Prepare module globals
    monkeypatch.setattr(log_module, "_RichHandlerWithEmoji", DummyRichHandler, raising=False)
    monkeypatch.setattr(log_module, "_LOG_LOCK", DummyLock(), raising=False)
    # Include two loggers: one will have a matching handler, one will have a non-matching handler
    monkeypatch.setattr(log_module, "_SET_UP_LOGGERS", ["test.logger.two", "test.logger.three"], raising=False)

    logger_name_matching = "test.logger.two"
    logger_name_nonmatching = "test.logger.three"

    logger_matching = logging.getLogger(logger_name_matching)
    logger_nonmatching = logging.getLogger(logger_name_nonmatching)
    # Ensure clean handlers list before test
    logger_matching.handlers[:] = []
    logger_nonmatching.handlers[:] = []

    try:
        # Handler with higher current level (numerically larger) should remain unchanged
        handler_high = DummyRichHandler(level=30)
        logger_matching.handlers.append(handler_high)

        # Add a non-matching handler type to the other logger to ensure isinstance branch is honored
        non_matching_handler = logging.StreamHandler()
        logger_nonmatching.handlers.append(non_matching_handler)

        # Call function to set stream level to 20 (should NOT call handler_high.setLevel)
        log_module.set_stream_handler_levels(20)

        # _STREAM_LEVEL should be updated to 20 regardless
        assert getattr(log_module, "_STREAM_LEVEL") == 20

        # Handler_high should not have been changed because its current_level (30) >= 20
        assert handler_high.set_calls == []
        assert handler_high.level == 30

        # Non-matching handler should be untouched and still be the same object in handlers list
        assert logger_nonmatching.handlers and logger_nonmatching.handlers[0] is non_matching_handler
    finally:
        # Cleanup handlers to avoid state pollution
        _cleanup_loggers([logger_name_matching, logger_name_nonmatching])
