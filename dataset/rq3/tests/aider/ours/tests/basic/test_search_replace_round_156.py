import pytest

from aider.coders import search_replace as sr


def test_returns_none_when_all_strategies_fail_round_156(monkeypatch):
    """If every try_strategy call is falsy, flexible_search_and_replace should
    iterate all (strategy, preproc) pairs and return None.
    """
    calls = []

    def fake_try_strategy(texts, strategy, preproc):
        # record each call and return a falsy value
        calls.append((tuple(texts), strategy, preproc))
        return None

    monkeypatch.setattr(sr, "try_strategy", fake_try_strategy)

    texts = ["original"]
    strategies = [("s1", ["p1", "p2"]), ("s2", ["p3"])]  # two strategies

    result = sr.flexible_search_and_replace(texts, strategies)

    assert result is None
    # ensure the function attempted every (strategy, preproc) pair in order
    assert calls == [
        (tuple(texts), "s1", "p1"),
        (tuple(texts), "s1", "p2"),
        (tuple(texts), "s2", "p3"),
    ]


def test_returns_first_truthy_result_round_156(monkeypatch):
    """If the first try_strategy call returns a truthy value, flexible_search_and_replace
    must return it immediately and not call try_strategy further.
    """
    calls = []

    def fake_try_strategy(texts, strategy, preproc):
        calls.append((strategy, preproc))
        # return a truthy sentinel on the very first call only
        if len(calls) == 1:
            return {"found": True, "strategy": strategy, "preproc": preproc}
        return None

    monkeypatch.setattr(sr, "try_strategy", fake_try_strategy)

    texts = ["orig"]
    strategies = [("first", ["a", "b"]), ("second", ["c"]) ]

    result = sr.flexible_search_and_replace(texts, strategies)

    assert result == {"found": True, "strategy": "first", "preproc": "a"}
    # must have short-circuited after the first truthy result
    assert calls == [("first", "a")]


def test_returns_first_truthy_later_round_156(monkeypatch):
    """When earlier try_strategy calls are falsy but a later one is truthy,
    flexible_search_and_replace should return that later truthy value.
    """
    calls = []

    # plan: falsy for first two calls, truthy on third
    def fake_try_strategy(texts, strategy, preproc):
        calls.append((strategy, preproc))
        if len(calls) == 3:
            return f"OK:{strategy}:{preproc}"
        return None

    monkeypatch.setattr(sr, "try_strategy", fake_try_strategy)

    texts = ["t1"]
    strategies = [("s1", ["p1", "p2"]), ("s2", ["p3"]) ]

    # call should proceed through s1:p1 (falsy), s1:p2 (falsy), then s2:p3 (truthy)
    result = sr.flexible_search_and_replace(texts, strategies)

    assert result == "OK:s2:p3"
    assert calls == [("s1", "p1"), ("s1", "p2"), ("s2", "p3")]
