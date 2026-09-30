import json
import pytest
from sweagent.tools.tools import ToolHandler


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # preserve exact call behavior: store the message
        self.warnings.append(msg)


class EnvRaisesFileNotFound:
    def read_file(self, path):
        raise FileNotFoundError()


class EnvEmptyFile:
    def __init__(self, content):
        self._content = content

    def read_file(self, path):
        return self._content


class DummySelf:
    def __init__(self):
        self.logger = DummyLogger()


def test_get_state_file_not_found_round_059():
    """If env.read_file raises FileNotFoundError, _get_state should return {} and log a warning."""
    dummy = DummySelf()
    env = EnvRaisesFileNotFound()

    result = ToolHandler._get_state(dummy, env)

    assert result == {}
    assert dummy.logger.warnings == ["State file not found, returning empty state"]


def test_get_state_empty_content_round_059():
    """If file content is whitespace-only, _get_state should return {} and log a warning."""
    dummy = DummySelf()
    env = EnvEmptyFile("   \n  \t  ")

    result = ToolHandler._get_state(dummy, env)

    assert result == {}
    assert dummy.logger.warnings == ["State file is empty, returning empty state"]


def test_get_state_invalid_json_round_059():
    """If file content is invalid JSON, _get_state should raise ValueError chaining the JSONDecodeError."""
    dummy = DummySelf()
    bad = "{"  # invalid JSON
    env = EnvEmptyFile(bad)

    with pytest.raises(ValueError) as excinfo:
        ToolHandler._get_state(dummy, env)

    # message must include the repr of the invalid content
    expected_msg = f"State {bad!r} is not valid json. This is an internal error, please report it."
    assert str(excinfo.value) == expected_msg
    # Ensure the original JSONDecodeError is the __cause__ of the ValueError
    assert isinstance(excinfo.value.__cause__, json.JSONDecodeError)


def test_get_state_non_dict_round_059():
    """If JSON parses but is not a dict, _get_state should raise ValueError with the precise message."""
    dummy = DummySelf()
    parsed = [1, 2, 3]
    env = EnvEmptyFile(json.dumps(parsed))

    with pytest.raises(ValueError) as excinfo:
        ToolHandler._get_state(dummy, env)

    expected_msg = f"State commands must return a dictionary. Got {parsed!r} instead."
    assert str(excinfo.value) == expected_msg


def test_get_state_valid_round_059():
    """Valid JSON dict should be returned unchanged."""
    dummy = DummySelf()
    payload = {"key": "value"}
    env = EnvEmptyFile(json.dumps(payload))

    result = ToolHandler._get_state(dummy, env)

    assert result == payload
