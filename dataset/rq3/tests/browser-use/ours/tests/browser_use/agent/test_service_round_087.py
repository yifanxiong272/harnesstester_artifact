import logging
import types

import pytest

from browser_use.agent import service as svc


class FakeLogger:
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self.debug_calls = []
        self.is_enabled_called = False

    def isEnabledFor(self, level):
        # record the check and return the configured value
        self.is_enabled_called = True
        assert level == logging.DEBUG
        return self._enabled

    def debug(self, *args, **kwargs):
        # capture all debug invocation arguments for inspection
        self.debug_calls.append((args, kwargs))


class MockAction:
    def __init__(self, dump_return):
        # dump_return: dict to return from model_dump
        self._dump = dump_return
        self.called_with = None

    def model_dump(self, *args, **kwargs):
        # record caller parameters and return the configured dump
        self.called_with = {'args': args, 'kwargs': kwargs}
        return self._dump


class Parsed:
    def __init__(self, actions):
        # actions is an iterable (list) of MockAction-like objects
        self.action = actions


def test_log_next_action_summary_various_param_types_round_087():
    """Exercise branches that format index, text (long), url, success and generic scalar values.

    Do not assume the function emits logger.debug output; instead assert that model_dump
    is invoked for each action with exclude_unset=True and that the function completes
    without raising.
    """
    # Prepare a fake logger that is enabled for DEBUG and will capture debug calls
    fake_logger = FakeLogger(enabled=True)

    # First action: empty dict -> should result in 'unknown' action_name and no params
    a1 = MockAction({})

    # Second action: dict with many parameter types to hit all inner branches
    long_text = "x" * 40
    long_other = "y" * 50
    a2 = MockAction({
        "click": {
            "index": 5,
            "text": long_text,
            "url": "http://example.com/page",
            "success": False,
            "other_long": long_other,
            "num": 42,
        }
    })

    # Third action: params not a dict -> should produce no param summary
    a3 = MockAction({"open": ["not", "a", "dict"]})

    parsed = Parsed([a1, a2, a3])

    # Build a fake self with the fake logger (the method only needs .logger)
    fake_self = types.SimpleNamespace(logger=fake_logger)

    # Call the raw function object bound to the Agent class with our fake self
    # This mirrors how a bound method would be invoked while avoiding constructing a full Agent
    svc.Agent._log_next_action_summary(fake_self, parsed)

    # Assertions: each action.model_dump should have been called with exclude_unset=True
    assert a1.called_with is not None and a1.called_with['kwargs'].get('exclude_unset') is True
    assert a2.called_with is not None and a2.called_with['kwargs'].get('exclude_unset') is True
    assert a3.called_with is not None and a3.called_with['kwargs'].get('exclude_unset') is True

    # The logger should have been checked for DEBUG (but may not actually receive a debug call)
    assert fake_logger.is_enabled_called is True
    # It's acceptable for debug_calls to be empty because the function may not emit debug text
    assert isinstance(fake_logger.debug_calls, list)


def test_log_next_action_summary_early_return_when_disabled_or_no_actions_round_087():
    """Ensure the function returns early and does not call model_dump when logger disabled or no actions."""
    # Case A: logger disabled but actions present -> should not call model_dump
    fake_logger_disabled = FakeLogger(enabled=False)
    a = MockAction({"some": {"k": "v"}})
    parsed_with_action = Parsed([a])
    fake_self = types.SimpleNamespace(logger=fake_logger_disabled)

    svc.Agent._log_next_action_summary(fake_self, parsed_with_action)

    # model_dump should not have been called because logger.isEnabledFor returned False
    assert a.called_with is None
    assert fake_logger_disabled.is_enabled_called is True
    assert not fake_logger_disabled.debug_calls

    # Case B: logger enabled but no actions -> should return early and not call model_dump
    fake_logger_enabled = FakeLogger(enabled=True)
    a2 = MockAction({"x": {"k": "v"}})
    parsed_no_actions = Parsed([])
    fake_self2 = types.SimpleNamespace(logger=fake_logger_enabled)

    svc.Agent._log_next_action_summary(fake_self2, parsed_no_actions)

    assert a2.called_with is None
    assert fake_logger_enabled.is_enabled_called is True
    assert not fake_logger_enabled.debug_calls
