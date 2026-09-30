# file: sweagent/agent/reviewer.py:299-305
# asked: {"lines": [301, 302, 303, 304, 305], "branches": []}
# gained: {"lines": [301, 302, 303, 304, 305], "branches": []}

import pytest

try:
    from sweagent.agent import reviewer
except Exception:
    pytest.skip("sweagent.agent.reviewer module not available", allow_module_level=True)


class LoggerStub:
    def __init__(self):
        self.last = None

    def error(self, msg):
        self.last = msg


def test_interpret_returns_last_number():
    # Create Chooser instance without calling __init__ to avoid heavy dependencies
    chooser = object.__new__(reviewer.Chooser)
    chooser.logger = LoggerStub()

    result = chooser.interpret("first 3 then 99 and finally 7")
    assert result == 7
    assert chooser.logger.last is None


def test_interpret_handles_exception_and_returns_zero(monkeypatch):
    chooser = object.__new__(reviewer.Chooser)
    chooser.logger = LoggerStub()

    def bad_findall(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(reviewer.re, "findall", bad_findall, raising=True)

    result = chooser.interpret("any input")
    assert result == 0
    assert chooser.logger.last is not None
    assert "Error interpreting response" in chooser.logger.last
    assert "boom" in chooser.logger.last
