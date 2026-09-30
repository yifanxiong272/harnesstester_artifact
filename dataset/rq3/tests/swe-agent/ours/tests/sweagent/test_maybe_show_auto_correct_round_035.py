import pytest

import sweagent.run.common as common


class _ACFalse:
    def __init__(self, text="alt"):
        self._text = text

    def show(self, args):
        # Always hidden
        return False

    def format(self):
        return self._text


class _ACTrue:
    def __init__(self, text="alt-true"):
        self._text = text

    def show(self, args):
        # Always shown
        return True

    def format(self):
        return self._text


def _make_instance_without_init():
    # Avoid running BasicCLI.__init__ which might have side effects; we only need an object
    inst = common.BasicCLI.__new__(common.BasicCLI)
    return inst


def test_no_get_auto_correct_round_035(monkeypatch):
    """
    If arg_type has no _get_auto_correct attribute, nothing should be printed.
    Covers branch where hasattr(self.arg_type, "_get_auto_correct") is False.
    """
    inst = _make_instance_without_init()
    # arg_type deliberately has no _get_auto_correct
    inst.arg_type = object()

    calls = []

    def fake_rich_print(x):
        calls.append(x)

    monkeypatch.setattr(common, "rich_print", fake_rich_print)

    inst.maybe_show_auto_correct(["some", "args"])

    # No calls to rich_print expected
    assert calls == [], "rich_print must not be called when no _get_auto_correct"


def test_get_auto_correct_all_false_round_035(monkeypatch):
    """
    If _get_auto_correct yields suggestions but all .show(args) return False,
    nothing should be printed and auto_correct stays empty.
    This covers the loop and the branch where no items are appended.
    """
    inst = _make_instance_without_init()

    class ArgType:
        def _get_auto_correct(self):
            return [_ACFalse("nope1"), _ACFalse("nope2")]

    inst.arg_type = ArgType()

    calls = []

    def fake_rich_print(x):
        calls.append(x)

    monkeypatch.setattr(common, "rich_print", fake_rich_print)

    inst.maybe_show_auto_correct(["x"])

    # No calls because all show() returned False
    assert calls == [], "rich_print must not be called when no suggestion shows True"


def test_get_auto_correct_some_true_round_035(monkeypatch):
    """
    If at least one suggestion's .show(args) returns True, Panel.fit should be used
    and its result passed to rich_print. We patch Panel.fit to return a predictable
    sentinel and assert rich_print receives that sentinel containing the formatted suggestion.
    This covers branches where items are appended and rich_print is invoked.
    """
    inst = _make_instance_without_init()

    class ArgType:
        def _get_auto_correct(self):
            # First suggestion hidden, second shown
            return [_ACFalse("hidden"), _ACTrue("suggestion-ok")]

    inst.arg_type = ArgType()

    captured = {}

    def fake_rich_print(obj):
        # capture the exact object passed to rich_print
        captured['value'] = obj

    class DummyPanel:
        @staticmethod
        def fit(text):
            # Return a predictable sentinel including the received text so we can assert
            return "PANEL:" + text

    monkeypatch.setattr(common, "rich_print", fake_rich_print)
    monkeypatch.setattr(common, "Panel", DummyPanel)

    test_args = ["arg1"]
    inst.maybe_show_auto_correct(test_args)

    # Build expected panel content exactly as in source
    expected_inner = (
        "[red][bold]Auto-correct suggestions[/bold][/red]\n\n"
        + "\n".join(["suggestion-ok"])  # only the shown suggestion's format()
    )
    assert 'value' in captured, "rich_print should be called when there are visible suggestions"
    assert captured['value'] == "PANEL:" + expected_inner
