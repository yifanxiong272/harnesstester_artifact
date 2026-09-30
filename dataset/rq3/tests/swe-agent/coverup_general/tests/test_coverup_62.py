# file: sweagent/agent/models.py:308-321
# asked: {"lines": [316, 317, 318, 319, 320, 321], "branches": [[315, 316], [318, 319], [318, 320]]}
# gained: {"lines": [316, 317, 318, 319, 320, 321], "branches": [[315, 316], [318, 319], [318, 320]]}

import pytest
from sweagent.agent.models import _handle_raise_commands
from sweagent.exceptions import FunctionCallingFormatError

def test_raise_function_calling_with_message():
    action = 'raise_function_calling ERR42 "detail message"'
    with pytest.raises(FunctionCallingFormatError) as excinfo:
        _handle_raise_commands(action)
    # The exception stores the original message and extra_info with error_code,
    # and its str()/args contain the combined message including the error_code tag.
    exc = excinfo.value
    assert exc.message == "detail message"
    assert exc.extra_info["error_code"] == "ERR42"
    assert exc.args == ("detail message [error_code=ERR42]",)
    assert str(exc) == "detail message [error_code=ERR42]"

def test_raise_function_calling_too_many_parts():
    # This will produce 4 parts and trigger the assertion len(parts) < 4
    action = "raise_function_calling a b c"
    with pytest.raises(AssertionError):
        _handle_raise_commands(action)
