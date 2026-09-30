import asyncio
import json
import logging
from types import SimpleNamespace

import pytest

from gpt_researcher.agent import GPTResearcher


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class DummyHandler:
    def __init__(self, raise_on=None):
        # raise_on can be 'tool', 'action', or 'research' to trigger exception path
        self.raise_on = raise_on
        self.calls = []

    async def on_tool_start(self, tool_name, **kwargs):
        if self.raise_on == 'tool':
            raise RuntimeError('handler tool failure')
        # record tool_name and kwargs for assertion
        self.calls.append(('tool', tool_name, dict(kwargs)))

    async def on_agent_action(self, action, **kwargs):
        if self.raise_on == 'action':
            raise RuntimeError('handler action failure')
        self.calls.append(('action', action, dict(kwargs)))

    async def on_research_step(self, step, details):
        if self.raise_on == 'research':
            raise RuntimeError('handler research failure')
        # details expected to be a mapping
        self.calls.append(('research', step, details))


def _attach_list_logger():
    logger = logging.getLogger('research')
    logger.setLevel(logging.INFO)
    list_handler = ListHandler()
    logger.addHandler(list_handler)
    return logger, list_handler


def _detach_list_logger(logger, list_handler):
    logger.removeHandler(list_handler)


def test_log_event_tool_with_handler_round_064():
    # Prepare a dummy self with a working log_handler
    dummy = SimpleNamespace()
    handler = DummyHandler()
    dummy.log_handler = handler

    logger, list_handler = _attach_list_logger()
    try:
        asyncio.run(GPTResearcher._log_event(dummy, 'tool', tool_name='hammer', extra='val'))

        # Handler should have been called with the provided tool_name and kwargs
        assert handler.calls == [('tool', 'hammer', {'tool_name': 'hammer', 'extra': 'val'})]

        # Backup logging should have recorded an info message containing the event_type and the JSON dump
        assert len(list_handler.records) >= 1
        last_msg = list_handler.records[-1].getMessage()
        assert last_msg.startswith('tool:')
        # JSON should contain the extra field
        assert '"extra": "val"' in last_msg
    finally:
        _detach_list_logger(logger, list_handler)


def test_log_event_action_with_handler_round_064():
    dummy = SimpleNamespace()
    handler = DummyHandler()
    dummy.log_handler = handler

    logger, list_handler = _attach_list_logger()
    try:
        asyncio.run(GPTResearcher._log_event(dummy, 'action', action='do_thing', meta=123))

        assert handler.calls == [('action', 'do_thing', {'action': 'do_thing', 'meta': 123})]

        assert len(list_handler.records) >= 1
        last_msg = list_handler.records[-1].getMessage()
        assert last_msg.startswith('action:')
        assert '"meta": 123' in last_msg
    finally:
        _detach_list_logger(logger, list_handler)


def test_log_event_research_with_handler_round_064():
    dummy = SimpleNamespace()
    handler = DummyHandler()
    dummy.log_handler = handler

    logger, list_handler = _attach_list_logger()
    try:
        # pass step and details explicitly to match the on_research_step signature
        asyncio.run(GPTResearcher._log_event(dummy, 'research', step='s1', details={'k': 'v'}))

        assert handler.calls == [('research', 's1', {'k': 'v'})]

        assert len(list_handler.records) >= 1
        last_msg = list_handler.records[-1].getMessage()
        assert last_msg.startswith('research:')
        # ensure details serialized into JSON
        assert '"k": "v"' in last_msg
    finally:
        _detach_list_logger(logger, list_handler)


def test_log_event_handler_raises_logs_error_round_064():
    dummy = SimpleNamespace()
    # Handler will raise when on_tool_start is invoked
    handler = DummyHandler(raise_on='tool')
    dummy.log_handler = handler

    logger, list_handler = _attach_list_logger()
    try:
        # When the handler raises, _log_event should catch and log an error
        asyncio.run(GPTResearcher._log_event(dummy, 'tool', tool_name='hammer'))

        # The handler call should not be recorded because it raised
        assert handler.calls == []

        # There should be at least one error-level record containing 'Error in _log_event'
        # The error record is emitted to the same 'research' logger in the except block
        error_records = [r for r in list_handler.records if r.levelno >= logging.ERROR]
        assert any('Error in _log_event' in r.getMessage() for r in error_records)
    finally:
        _detach_list_logger(logger, list_handler)


def test_log_event_without_handler_still_logs_round_064():
    dummy = SimpleNamespace()
    dummy.log_handler = None

    logger, list_handler = _attach_list_logger()
    try:
        asyncio.run(GPTResearcher._log_event(dummy, 'unknown_event', foo='bar'))

        # No handler calls expected
        # Just ensure the backup logging recorded the event and kwargs
        assert len(list_handler.records) >= 1
        msg = list_handler.records[-1].getMessage()
        assert msg.startswith('unknown_event:')
        assert '"foo": "bar"' in msg
    finally:
        _detach_list_logger(logger, list_handler)
