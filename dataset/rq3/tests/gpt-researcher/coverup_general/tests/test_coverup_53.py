# file: gpt_researcher/utils/tools.py:274-316
# asked: {"lines": [292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 305, 306, 307, 308, 310, 313, 314, 316], "branches": [[305, 306], [305, 307], [307, 308], [307, 310]]}
# gained: {"lines": [292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 305, 306, 307, 308, 310, 313, 314, 316], "branches": [[305, 306], [305, 307], [307, 308], [307, 310]]}

import importlib
import pytest


def _setup_identity_tool(monkeypatch, tools_mod):
    # Make sure the @tool decorator used inside create_custom_tool is an identity decorator
    monkeypatch.setattr(tools_mod, "tool", lambda f: f, raising=True)


class DummyLogger:
    def __init__(self):
        self.calls = []

    def error(self, msg, exc_info=False):
        self.calls.append((msg, exc_info))


def test_custom_tool_success_non_none(monkeypatch):
    tools_mod = importlib.import_module("gpt_researcher.utils.tools")
    _setup_identity_tool(monkeypatch, tools_mod)

    def simple_func():
        return 123

    # Ensure logger exists (not strictly needed for success path but keeps environment consistent)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_mod, "logger", dummy_logger, raising=False)

    custom_tool = tools_mod.create_custom_tool("my_tool", "does math", simple_func)
    assert callable(custom_tool)
    # result should be stringified
    result = custom_tool()
    assert result == "123"
    assert getattr(custom_tool, "name") == "my_tool"
    assert getattr(custom_tool, "description") == "does math"
    # logger should not have recorded errors
    assert dummy_logger.calls == []


def test_custom_tool_success_none(monkeypatch):
    tools_mod = importlib.import_module("gpt_researcher.utils.tools")
    _setup_identity_tool(monkeypatch, tools_mod)

    def none_func():
        return None

    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_mod, "logger", dummy_logger, raising=False)

    custom_tool = tools_mod.create_custom_tool("none_tool", "returns none", none_func)
    result = custom_tool()
    assert result == "Tool executed successfully"
    assert dummy_logger.calls == []


def test_custom_tool_validation_error(monkeypatch):
    tools_mod = importlib.import_module("gpt_researcher.utils.tools")
    _setup_identity_tool(monkeypatch, tools_mod)

    def bad_func(*args, **kwargs):
        raise Exception("Validation failed: field is invalid")

    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_mod, "logger", dummy_logger, raising=False)

    custom_tool = tools_mod.create_custom_tool("val_tool", "validates", bad_func)
    result = custom_tool()
    assert (
        result
        == "Tool 'val_tool' received invalid input. Please check the parameters and try again."
    )
    # logger.error should have been called once with exc_info True
    assert len(dummy_logger.calls) == 1
    msg, exc_info = dummy_logger.calls[0]
    assert "Custom tool 'val_tool' error" in msg
    assert exc_info is True


def test_custom_tool_not_found_error(monkeypatch):
    tools_mod = importlib.import_module("gpt_researcher.utils.tools")
    _setup_identity_tool(monkeypatch, tools_mod)

    def missing_func():
        raise Exception("File not found: config.json")

    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_mod, "logger", dummy_logger, raising=False)

    custom_tool = tools_mod.create_custom_tool("find_tool", "finds files", missing_func)
    result = custom_tool()
    assert (
        result
        == "Tool 'find_tool' could not find required resources. Please verify the input data is correct."
    )
    # logger recorded the error
    assert len(dummy_logger.calls) == 1
    assert dummy_logger.calls[0][1] is True


def test_custom_tool_other_error(monkeypatch):
    tools_mod = importlib.import_module("gpt_researcher.utils.tools")
    _setup_identity_tool(monkeypatch, tools_mod)

    def boom_func():
        raise Exception("unexpected boom")

    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_mod, "logger", dummy_logger, raising=False)

    custom_tool = tools_mod.create_custom_tool("boom_tool", "explodes", boom_func)
    result = custom_tool()
    assert result == "Tool 'boom_tool' encountered an error: unexpected boom. Please check the tool configuration."
    # logger recorded the error
    assert len(dummy_logger.calls) == 1
    assert dummy_logger.calls[0][1] is True
