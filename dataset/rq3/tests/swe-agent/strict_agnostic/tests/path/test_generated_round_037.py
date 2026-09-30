import pytest
from types import SimpleNamespace
from sweagent.run import common

# Tests for BasicCLI.maybe_show_auto_correct covering branches where
# - self.arg_type has no _get_auto_correct
# - self.arg_type._get_auto_correct exists but returns empty
# - self.arg_type._get_auto_correct yields suggestions, some show() True some False
# We patch common.rich_print to avoid real output and to observe calls.

def _make_self_with_arg_type(arg_type):
    # Create a minimal self object with the expected attribute
    return SimpleNamespace(arg_type=arg_type)


def test_no_get_auto_correct_round_037(monkeypatch):
    """When arg_type has no _get_auto_correct, rich_print must not be called."""
    called = {"count": 0}

    def fake_rich_print(*args, **kwargs):
        called["count"] += 1

    # Ensure attr is absent
    arg_type = SimpleNamespace()
    self = _make_self_with_arg_type(arg_type)

    monkeypatch.setattr(common, "rich_print", fake_rich_print)

    # Call the method directly with our minimal self
    common.BasicCLI.maybe_show_auto_correct(self, ["anything"])

    assert called["count"] == 0, "rich_print should not be called when no _get_auto_correct"


def test_get_auto_correct_empty_round_037(monkeypatch):
    """When _get_auto_correct exists but returns an empty iterable, nothing is printed."""
    called = {"count": 0}

    def fake_rich_print(*args, **kwargs):
        called["count"] += 1

    class ArgType:
        @staticmethod
        def _get_auto_correct():
            return []

    self = _make_self_with_arg_type(ArgType())

    monkeypatch.setattr(common, "rich_print", fake_rich_print)

    common.BasicCLI.maybe_show_auto_correct(self, ["x"])

    assert called["count"] == 0, "rich_print should not be called when _get_auto_correct returns empty"


def test_get_auto_correct_with_suggestions_round_037(monkeypatch):
    """When at least one suggestion.show(args) is True, rich_print should be called
    and the Panel content should include the formatted suggestion string.
    """
    captured = {"args": None}

    def fake_rich_print(arg):
        # capture the single positional argument passed to rich_print
        captured["args"] = arg

    class ACFalse:
        def show(self, args):
            return False

        def format(self):
            return "should-not-appear"

    class ACTrue:
        def show(self, args):
            # Return True to trigger inclusion in auto_correct
            return True

        def format(self):
            return "suggestion-1"

    class ArgType:
        @staticmethod
        def _get_auto_correct():
            # Return a mixture to exercise both branches inside the loop
            return [ACFalse(), ACTrue()]

    self = _make_self_with_arg_type(ArgType())

    monkeypatch.setattr(common, "rich_print", fake_rich_print)

    common.BasicCLI.maybe_show_auto_correct(self, ["some", "args"])

    # Ensure rich_print was called with a Panel instance
    assert captured["args"] is not None, "rich_print should have been called"
    panel = captured["args"]
    # The module uses rich.panel.Panel; ensure the captured object is a Panel
    assert isinstance(panel, common.Panel), f"Expected a Panel instance, got {type(panel)!r}"

    # The Panel.renderable should contain the header text and the formatted suggestion
    renderable_text = str(getattr(panel, "renderable", panel))
    assert "Auto-correct suggestions" in renderable_text
    assert "suggestion-1" in renderable_text
