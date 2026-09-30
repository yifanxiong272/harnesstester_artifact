# file: aider/coders/search_replace.py:565-577
# asked: {"lines": [573, 574, 575, 576, 577], "branches": [[573, 0], [573, 574], [574, 573], [574, 575], [576, 574], [576, 577]]}
# gained: {"lines": [573, 574, 575, 576, 577], "branches": [[573, 0], [573, 574], [574, 573], [574, 575], [576, 574], [576, 577]]}

import importlib
import pytest

search_replace = importlib.import_module("aider.coders.search_replace")


def test_flexible_search_and_replace_returns_first_truthy(monkeypatch):
    calls = []

    def fake_try_strategy(texts, strategy, preproc):
        # record the call
        calls.append((texts, strategy, preproc))
        # only return a truthy value for a specific combination
        if strategy == "s1" and preproc == "p2":
            return {"matched": True, "strategy": strategy, "preproc": preproc}
        return None

    monkeypatch.setattr(search_replace, "try_strategy", fake_try_strategy)

    texts = ["line1", "line2"]
    strategies = [
        ("s1", ["p1", "p2"]),  # first strategy: second preproc should hit and return truthy
        ("s2", ["p3"]),        # should not be reached
    ]

    res = search_replace.flexible_search_and_replace(texts, strategies)

    assert res == {"matched": True, "strategy": "s1", "preproc": "p2"}
    # ensure try_strategy was called in the expected order and that it stopped after the truthy result
    assert calls == [
        (texts, "s1", "p1"),
        (texts, "s1", "p2"),
    ]


def test_flexible_search_and_replace_returns_none_when_no_strategy_matches(monkeypatch):
    calls = []

    def fake_try_strategy(texts, strategy, preproc):
        calls.append((strategy, preproc))
        # always falsy
        return 0

    monkeypatch.setattr(search_replace, "try_strategy", fake_try_strategy)

    texts = "dummy"
    strategies = [
        ("alpha", ["one"]),
        ("beta", ["two", "three"]),
    ]

    res = search_replace.flexible_search_and_replace(texts, strategies)

    # when no strategy returns a truthy result, function should return None
    assert res is None
    # verify all expected calls were made
    assert calls == [
        ("alpha", "one"),
        ("beta", "two"),
        ("beta", "three"),
    ]
