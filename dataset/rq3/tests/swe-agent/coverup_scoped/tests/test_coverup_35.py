# file: sweagent/tools/tools.py:298-316
# asked: {"lines": [302, 303, 304, 310, 311, 312, 314, 315], "branches": [[313, 314]]}
# gained: {"lines": [302, 303, 304, 310, 311, 312, 314, 315], "branches": [[313, 314]]}

import json
import pytest

from sweagent.tools.tools import ToolHandler


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        self.warnings.append(msg)


class EnvFileNotFound:
    def read_file(self, path: str) -> str:
        raise FileNotFoundError("no file")


class EnvInvalidJSON:
    def __init__(self, content: str):
        self._content = content

    def read_file(self, path: str) -> str:
        return self._content


class EnvNonDictJSON:
    def __init__(self, content: str):
        self._content = content

    def read_file(self, path: str) -> str:
        return self._content


def make_handler_with_logger():
    # create instance without running __init__ to avoid needing ToolConfig
    handler = object.__new__(ToolHandler)
    handler.logger = DummyLogger()
    return handler


def test_get_state_file_not_found_returns_empty_and_logs_warning():
    handler = make_handler_with_logger()
    env = EnvFileNotFound()

    result = handler._get_state(env)
    assert result == {}, "Expected empty dict when state file is missing"
    assert handler.logger.warnings, "Expected a warning to be logged"
    assert any("State file not found" in w for w in handler.logger.warnings)


def test_get_state_invalid_json_raises_value_error_with_cause():
    handler = make_handler_with_logger()
    env = EnvInvalidJSON("not-a-json")

    with pytest.raises(ValueError) as excinfo:
        handler._get_state(env)

    exc = excinfo.value
    expected_msg = "State 'not-a-json' is not valid json. This is an internal error, please report it."
    assert str(exc) == expected_msg
    # The ValueError should be raised from a JSONDecodeError
    assert isinstance(exc.__cause__, json.JSONDecodeError)


def test_get_state_non_dict_json_raises_value_error():
    handler = make_handler_with_logger()
    # JSON that decodes to a list, not a dict
    env = EnvNonDictJSON('["a", "b"]')

    with pytest.raises(ValueError) as excinfo:
        handler._get_state(env)

    exc = excinfo.value
    assert str(exc) == "State commands must return a dictionary. Got ['a', 'b'] instead."
