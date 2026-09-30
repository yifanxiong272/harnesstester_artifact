import types

import pytest

from browser_use.tools import service


class DummyLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg):
        # Record debug calls for assertions
        self.messages.append(msg)


def _call_validator_with_logger(input_code: str):
    """Helper to call the class-bound function without instantiating Tools.

    The method is defined on Tools but does not use `self` at all, so we
    pass a dummy object as `self`.
    """
    dummy_self = object()
    return service.Tools._validate_and_fix_javascript(dummy_self, input_code)


def test_validate_and_fix_javascript_changes_round_091(monkeypatch):
    # Arrange: patch module logger to capture debug calls deterministically
    dummy_logger = DummyLogger()
    monkeypatch.setattr(service, "logger", dummy_logger)

    # Input contains:
    # - document.evaluate("...") -> should become backtick template literal
    # - querySelector("...") -> should become backtick template literal
    # - .closest("...") and .matches("...") -> backtick replacements
    # - an escaped quote sequence r'\"' that should be fixed to '"'
    input_code = r'''document.evaluate("/some/xpath", doc);
el.querySelector("div > span");
node.closest("a.link");
node.matches(".active");
var s = \"quoted\";
'''

    # Act
    fixed = _call_validator_with_logger(input_code)

    # Assert replacements happened
    assert "document.evaluate(`/some/xpath`," in fixed
    assert "el.querySelector(`div > span`)" in fixed
    assert "node.closest(`a.link`)" in fixed
    assert "node.matches(`.active`)" in fixed

    # The original escaped-quote token (backslash + quote) should be gone
    assert r'\"' not in fixed

    # Since we introduced template literals, a backtick should now appear
    assert "`" in fixed

    # Logger.debug must have been called once with the expected prefix
    assert any("JavaScript fixes applied:" in m for m in dummy_logger.messages)


def test_validate_and_fix_javascript_no_changes_round_091(monkeypatch):
    # Arrange: patch module logger again
    dummy_logger = DummyLogger()
    monkeypatch.setattr(service, "logger", dummy_logger)

    # Input that should not trigger any of the replacement patterns
    input_code = 'const a = "plain"; // no mixed quotes patterns here\n'

    # Act
    fixed = _call_validator_with_logger(input_code)

    # Assert: unchanged
    assert fixed == input_code

    # No debug logging since no changes should be made
    assert dummy_logger.messages == []
