# file: aider/coders/search_replace.py:565-577
# asked: {"lines": [573, 574, 575, 576, 577], "branches": [[573, 0], [573, 574], [574, 573], [574, 575], [576, 574], [576, 577]]}
# gained: {"lines": [573, 574, 575, 576, 577], "branches": [[573, 0], [573, 574], [574, 573], [574, 575], [576, 574], [576, 577]]}

import pytest

from aider.coders import search_replace


def test_flexible_search_and_replace_returns_on_first_truthy(monkeypatch):
    texts = ["one", "two"]

    # Prepare strategies: two strategies, first with two preprocs, second with one.
    strategies = [
        ("strategy1", ["pre1", "pre2"]),
        ("strategy2", ["preA"]),
    ]

    calls = []

    # fake try_strategy: return None for first call, a truthy value for the second,
    # and raise if called beyond expected (to catch over-iteration).
    def fake_try_strategy(in_texts, strategy, preproc):
        calls.append((strategy, preproc, list(in_texts)))
        if (strategy, preproc) == ("strategy1", "pre1"):
            return None
        if (strategy, preproc) == ("strategy1", "pre2"):
            return {"result": "matched"}  # truthy -> should cause early return
        raise AssertionError("try_strategy called unexpectedly with %s %s" % (strategy, preproc))

    monkeypatch.setattr(search_replace, "try_strategy", fake_try_strategy)

    res = search_replace.flexible_search_and_replace(texts, strategies)

    # Should have returned the truthy result from ("strategy1","pre2")
    assert res == {"result": "matched"}

    # Ensure try_strategy was called exactly twice (stopped after a truthy result)
    assert calls == [
        ("strategy1", "pre1", texts),
        ("strategy1", "pre2", texts),
    ]


def test_flexible_search_and_replace_returns_none_when_no_strategy_matches(monkeypatch):
    texts = ["alpha", "beta"]

    strategies = [
        ("sA", ["p1", "p2"]),
        ("sB", ["p3"]),
    ]

    calls = []

    # fake try_strategy always returns falsy (None). Record calls.
    def fake_try_strategy_all_none(in_texts, strategy, preproc):
        calls.append((strategy, preproc, list(in_texts)))
        return None

    monkeypatch.setattr(search_replace, "try_strategy", fake_try_strategy_all_none)

    res = search_replace.flexible_search_and_replace(texts, strategies)

    # When no strategy yields a truthy result, function should return None
    assert res is None

    # Ensure try_strategy was called for every (strategy, preproc) pair in order.
    expected_calls = [
        ("sA", "p1", texts),
        ("sA", "p2", texts),
        ("sB", "p3", texts),
    ]
    assert calls == expected_calls
