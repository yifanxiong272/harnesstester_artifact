import types
import copy
import pytest

import openhands.llm.llm_utils as lu
from openhands.llm.llm_utils import check_tools


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg):
        # deterministic capture of info messages
        self.messages.append(str(msg))


def test_gemini_removes_defaults_and_unsupported_formats_round_070(monkeypatch):
    """Gemini model: defaults removed and unsupported string formats removed; supported formats kept.

    Also verify original tools are not mutated (deepcopy) and logger.info is invoked.
    """
    dummy = DummyLogger()
    monkeypatch.setattr(lu, "logger", dummy)

    tools = [
        {
            "function": {
                "parameters": {
                    "properties": {
                        "a": {"type": "string", "format": "uuid", "default": "x"},
                        "b": {"type": "string", "format": "enum", "default": "y"},
                        "c": {"type": "integer", "default": 5},
                    }
                }
            }
        }
    ]

    # Use a simple namespace to mimic LLMConfig with a model attribute
    llm_config = types.SimpleNamespace(model="gemini-advanced")

    # Keep a deep copy of original to ensure the input is not mutated
    original_copy = copy.deepcopy(tools)

    checked = check_tools(tools, llm_config)

    # Should return a deep-copied list, not the exact same object
    assert checked is not tools
    assert checked == original_copy or checked != tools

    props = checked[0]["function"]["parameters"]["properties"]

    # 'a' had unsupported format 'uuid' and a default -> both should be removed
    assert "default" not in props["a"]
    assert "format" not in props["a"]

    # 'b' had supported format 'enum' -> format should remain, default removed
    assert props["b"].get("format") == "enum"
    assert "default" not in props["b"]

    # 'c' is integer and had a default -> default should be removed
    assert "default" not in props["c"]

    # Logger should have been called at least for removal notice and unsupported-format notice
    assert len(dummy.messages) >= 2
    assert any("Removing unsupported format" in m for m in dummy.messages)

    # original input must remain unchanged
    assert tools == original_copy


def test_non_gemini_returns_original_round_070():
    """Non-Gemini models should return the original tools object unchanged."""
    tools = [{"some": "tool"}]
    llm_config = types.SimpleNamespace(model="gpt-4")

    result = check_tools(tools, llm_config)

    # For non-gemini models, function returns the same object (no deepcopy)
    assert result is tools


def test_tool_without_function_or_parameters_round_070(monkeypatch):
    """Tools missing 'function' or missing 'parameters' or missing 'properties' should be handled safely.

    The function should still return a deep-copied structure and not raise.
    """
    dummy = DummyLogger()
    monkeypatch.setattr(lu, "logger", dummy)

    tools = [
        {"no_function": True},
        {"function": {}},
        {"function": {"parameters": {}}},
    ]

    llm_config = types.SimpleNamespace(model="gemini-mini")

    original = copy.deepcopy(tools)
    checked = check_tools(tools, llm_config)

    # Should return a deep copy
    assert checked is not tools
    # Structure should be preserved for entries without properties
    assert checked == original

    # Ensure no exceptions occurred and logger was used for Gemini entry (initial info)
    assert len(dummy.messages) >= 1
