# file: sweagent/agent/models.py:308-321
# asked: {"lines": [316, 317, 318, 319, 320, 321], "branches": [[315, 316], [318, 319], [318, 320]]}
# gained: {"lines": [316, 317, 318, 319, 320, 321], "branches": [[315, 316], [318, 319], [318, 320]]}

import pytest

from sweagent.agent.models import _handle_raise_commands
from sweagent.exceptions import FunctionCallingFormatError


def test_handle_raise_function_calling_raises_function_calling_format_error():
    action = 'raise_function_calling missing "this is the message"'
    with pytest.raises(FunctionCallingFormatError) as excinfo:
        _handle_raise_commands(action)

    err = excinfo.value
    # Check the stored message and extra_info populated as expected
    assert getattr(err, "message") == "this is the message"
    assert isinstance(err.extra_info, dict)
    assert err.extra_info.get("error_code") == "missing"
    # The exception string includes the appended [error_code=...]
    assert " [error_code=missing]" in str(err)


def test_handle_raise_function_calling_asserts_on_too_many_parts():
    # This action will split into 4 parts, triggering the assert len(parts) < 4
    action = 'raise_function_calling missing "msg1" extra'
    with pytest.raises(AssertionError):
        _handle_raise_commands(action)
