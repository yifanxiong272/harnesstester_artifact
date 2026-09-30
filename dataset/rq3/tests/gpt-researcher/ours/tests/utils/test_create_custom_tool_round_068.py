import functools
import pytest

from gpt_researcher.utils import tools


# Provide a simple no-op decorator to replace the langchain 'tool' decorator
# so that create_custom_tool can be tested deterministically without importing
# or calling any external libraries.
def _noop_tool_decorator(fn):
    # preserve metadata but return the original callable
    return functools.wraps(fn)(fn)


def test_custom_tool_success_round_068(monkeypatch):
    """Custom tool should return stringified results and handle None returns."""
    # Patch the decorator used inside create_custom_tool so the inner function
    # is not transformed by external libs.
    monkeypatch.setattr(tools, "tool", _noop_tool_decorator)

    def sample_add(a, b=0):
        return {"a": a, "b": b, "sum": a + b}

    custom = tools.create_custom_tool("adder", "adds two numbers", sample_add)

    # metadata is set on the returned callable
    assert hasattr(custom, "name") and custom.name == "adder"
    assert hasattr(custom, "description") and custom.description == "adds two numbers"

    # calling returns the stringified result
    out = custom(2, b=3)
    assert out == str({"a": 2, "b": 3, "sum": 5})

    # function returning None should yield the success message
    def returns_none():
        return None

    custom_none = tools.create_custom_tool("none_tool", "returns none", returns_none)
    assert custom_none() == "Tool executed successfully"


def test_custom_tool_validation_error_round_068(monkeypatch):
    """Errors mentioning 'validation' or 'invalid' should return the validation message."""
    monkeypatch.setattr(tools, "tool", _noop_tool_decorator)

    def bad_input():
        raise ValueError("Validation failed: missing required field")

    t = tools.create_custom_tool("val_tool", "validates input", bad_input)
    res = t()
    assert res == "Tool 'val_tool' received invalid input. Please check the parameters and try again."


def test_custom_tool_not_found_error_round_068(monkeypatch):
    """Errors mentioning 'not found' or 'missing' should return the resource-not-found message."""
    monkeypatch.setattr(tools, "tool", _noop_tool_decorator)

    def missing_resource():
        raise RuntimeError("Resource not found in storage")

    t = tools.create_custom_tool("finder", "finds resources", missing_resource)
    res = t()
    assert res == "Tool 'finder' could not find required resources. Please verify the input data is correct."


def test_custom_tool_generic_error_round_068(monkeypatch):
    """Any other exception should return the generic error message including the original message."""
    monkeypatch.setattr(tools, "tool", _noop_tool_decorator)

    def blows_up():
        raise Exception("boom")

    t = tools.create_custom_tool("exploder", "explodes", blows_up)
    res = t()
    assert res == "Tool 'exploder' encountered an error: boom. Please check the tool configuration."
