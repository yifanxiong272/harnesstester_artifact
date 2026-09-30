import pytest

from sweagent.agent.reviewer import Chooser


class DummyLogger:
    def __init__(self):
        self.messages = []

    def error(self, msg: str):
        # Capture the exact message for assertions
        self.messages.append(msg)


def make_chooser_with_logger(logger=None):
    # Construct Chooser without calling __init__ to avoid get_model/get_logger side effects
    chooser = object.__new__(Chooser)
    chooser.logger = logger or DummyLogger()
    return chooser


def test_interpret_returns_last_number_round_073():
    chooser = make_chooser_with_logger()

    # last number in the string should be returned as int
    result = chooser.interpret("option 7 then option 42")
    assert isinstance(result, int)
    assert result == 42


def test_interpret_handles_no_numbers_and_logs_round_073():
    dummy = DummyLogger()
    chooser = make_chooser_with_logger(logger=dummy)

    # No digits in the response should trigger the exception branch and return 0
    result = chooser.interpret("there are no digits here")
    assert result == 0

    # Ensure logger.error was called and message includes the expected prefix
    assert dummy.messages, "logger.error was not called"
    assert any("Error interpreting response:" in m for m in dummy.messages)


def test_interpret_parses_leading_zero_round_073():
    chooser = make_chooser_with_logger()

    # Leading zeros should be handled by int() conversion ("01" -> 1)
    result = chooser.interpret("first 0, then 01")
    assert result == 1
