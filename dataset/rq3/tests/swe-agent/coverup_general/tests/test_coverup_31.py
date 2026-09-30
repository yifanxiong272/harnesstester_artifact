# file: sweagent/run/common.py:205-217
# asked: {"lines": [206, 207, 208, 209, 210, 211, 212, 213, 214, 215], "branches": [[207, 208], [207, 211], [208, 209], [208, 211], [209, 208], [209, 210], [211, 0], [211, 212]]}
# gained: {"lines": [206, 207, 208, 209, 210, 211, 212, 213, 214, 215], "branches": [[207, 208], [208, 209], [208, 211], [209, 208], [209, 210], [211, 0], [211, 212]]}

import pytest

import sweagent.run.common as common
from sweagent.run.common import BasicCLI


class DummySuggestion:
    def __init__(self, name: str, show_result: bool):
        self._name = name
        self._show_result = show_result

    def show(self, args):
        return self._show_result

    def format(self):
        return f"formatted:{self._name}"


class DummyArgTypeWithSuggestions:
    @staticmethod
    def _get_auto_correct():
        return [DummySuggestion("one", True), DummySuggestion("two", True)]


class DummyArgTypeWithNoShownSuggestions:
    @staticmethod
    def _get_auto_correct():
        return [DummySuggestion("a", False), DummySuggestion("b", False)]


def test_maybe_show_auto_correct_prints_suggestions(monkeypatch):
    printed = []

    def fake_print(arg, *args, **kwargs):
        # capture what BasicCLI passes (Panel.fit(...) result)
        printed.append(arg)

    class FakePanel:
        @staticmethod
        def fit(content):
            return f"FIT[{content}]"

    # Patch names in the sweagent.run.common module where they were imported at module import time
    monkeypatch.setattr(common, "rich_print", fake_print, raising=True)
    monkeypatch.setattr(common, "Panel", FakePanel, raising=True)

    cli = BasicCLI(DummyArgTypeWithSuggestions)
    cli.maybe_show_auto_correct(["some", "args"])

    assert len(printed) == 1

    expected_inner = "[red][bold]Auto-correct suggestions[/bold][/red]\n\n" + "\n".join(
        s.format() for s in DummyArgTypeWithSuggestions._get_auto_correct()
    )
    expected = f"FIT[{expected_inner}]"
    assert printed[0] == expected


def test_maybe_show_auto_correct_with_no_shown_suggestions_does_not_print(monkeypatch):
    printed = []

    def fake_print(arg, *args, **kwargs):
        printed.append(arg)

    class FakePanel:
        @staticmethod
        def fit(content):
            return f"FIT[{content}]"

    monkeypatch.setattr(common, "rich_print", fake_print, raising=True)
    monkeypatch.setattr(common, "Panel", FakePanel, raising=True)

    cli = BasicCLI(DummyArgTypeWithNoShownSuggestions)
    cli.maybe_show_auto_correct([])

    # No suggestions should have been printed because all .show() returned False
    assert printed == []
