import pytest

from sweagent.agent.models import _handle_raise_commands
from swerex.exceptions import SwerexException
from sweagent.exceptions import (
    CostLimitExceededError,
    ContextWindowExceededError,
    FunctionCallingFormatError,
)


def test_raise_runtime_round_052():
    """Ensure the 'raise_runtime' action raises SwerexException."""
    with pytest.raises(SwerexException):
        _handle_raise_commands("raise_runtime")


def test_raise_cost_round_052():
    """Ensure the 'raise_cost' action raises CostLimitExceededError."""
    with pytest.raises(CostLimitExceededError):
        _handle_raise_commands("raise_cost")


def test_raise_context_round_052():
    """Ensure the 'raise_context' action raises ContextWindowExceededError."""
    with pytest.raises(ContextWindowExceededError):
        _handle_raise_commands("raise_context")


def test_raise_function_calling_with_message_round_052():
    """When action includes an error code and a quoted message, the
    FunctionCallingFormatError is raised and receives (message, code)
    as its constructor args."""
    # Use quoting so shlex.split produces a single message token with spaces
    action = 'raise_function_calling ERR42 "a nuanced message"'
    with pytest.raises(FunctionCallingFormatError) as excinfo:
        _handle_raise_commands(action)

    exc = excinfo.value
    # The function constructs the exception with (error_message, error_code)
    assert exc.args[0] == "a nuanced message"
    assert exc.args[1] == "ERR42"


def test_raise_function_calling_missing_message_round_052():
    """When the action has only the error code (no message), the local
    variable error_message is never set and referencing it raises
    an UnboundLocalError before constructing FunctionCallingFormatError.
    This covers the branch where len(parts) != 3.
    """
    action = "raise_function_calling ERR99"
    with pytest.raises(UnboundLocalError):
        _handle_raise_commands(action)
