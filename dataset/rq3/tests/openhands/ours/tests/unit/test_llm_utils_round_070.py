import copy
import importlib

import openhands.llm.llm_utils as llm_utils
from openhands.llm.llm_utils import check_tools


class DummyLLMConfig:
    def __init__(self, model: str):
        self.model = model


class _FakeLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        # store as string for deterministic assertions
        self.infos.append(str(msg))


def test_non_gemini_return_original_round_070():
    """Non-gemini models should return the original tools object unchanged (no deepcopy)."""
    config = DummyLLMConfig("gpt-4")
    tools = [{"function": {"parameters": {"properties": {"a": {"type": "string"}}}}}]

    # For non-Gemini models the function should return the original list object
    result = check_tools(tools, config)
    assert result is tools
    # ensure content unchanged
    assert result[0]["function"]["parameters"]["properties"]["a"]["type"] == "string"


def test_gemini_removes_default_and_unsupported_format_and_logs_round_070(monkeypatch):
    """Gemini path: default fields removed from any property; unsupported string formats removed and logged.

    Also ensure original input is not mutated (deepcopy behavior).
    """
    fake_logger = _FakeLogger()
    # Patch the logger symbol where the module resolves it
    monkeypatch.setattr(llm_utils, "logger", fake_logger)

    tools = [
        {
            "function": {
                "parameters": {
                    "properties": {
                        "p1": {"type": "string", "default": 42, "format": "uri"},
                        "p2": {"type": "string", "format": "date-time"},
                        "p3": {"type": "integer", "default": 1, "format": "something"},
                    }
                }
            }
        }
    ]

    # original copy to assert no mutation
    original_tools = copy.deepcopy(tools)

    config = DummyLLMConfig("Gemini-Preview-Model")
    result = check_tools(tools, config)

    # The function returns a deepcopy for Gemini, so returned object should not be the same instance
    assert result is not tools

    # Original must remain unchanged
    assert original_tools == tools
    assert tools[0]["function"]["parameters"]["properties"]["p1"]["default"] == 42
    assert tools[0]["function"]["parameters"]["properties"]["p1"]["format"] == "uri"

    # In the result: defaults should be removed for all properties
    rp = result[0]["function"]["parameters"]["properties"]
    assert "default" not in rp["p1"]
    assert "default" not in rp["p3"]

    # Unsupported format 'uri' should be removed for string p1
    assert "format" not in rp["p1"]

    # Supported format should be preserved
    assert rp["p2"]["format"] == "date-time"

    # Logging: initial info about removing defaults + specific unsupported-format message for p1
    # Ensure at least one message mentions unsupported format and the initial explanatory message is present
    joined = "\n".join(fake_logger.infos)
    assert "Removing default fields and unsupported formats" in joined
    assert "Removing unsupported format" in joined and "p1" in joined


def test_gemini_handles_missing_keys_round_070(monkeypatch):
    """Ensure code is robust when tools lack 'function', 'parameters', or 'properties' keys: no exceptions, returns deepcopy."""
    fake_logger = _FakeLogger()
    monkeypatch.setattr(llm_utils, "logger", fake_logger)

    tools = [
        {"name": "no_function"},
        {"function": {}},
        {"function": {"parameters": {}}},
    ]

    config = DummyLLMConfig("gemini-2")

    result = check_tools(tools, config)

    # Should return a deepcopy and preserve structure (no exceptions thrown)
    assert result == tools
    assert result is not tools
    assert len(result) == 3

    # The module should have logged the initial Gemini explanatory message
    assert any("Removing default fields and unsupported formats" in m for m in fake_logger.infos)
