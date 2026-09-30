# file: aider/coders/search_replace.py:586-608
# asked: {"lines": [587, 588, 590, 591, 592, 593, 594, 595, 597, 599, 600, 602, 603, 604, 605, 606, 608], "branches": [[590, 591], [590, 592], [592, 593], [592, 594], [594, 595], [594, 597], [599, 600], [599, 602], [602, 603], [602, 608]]}
# gained: {"lines": [587, 588, 590, 591, 592, 593, 594, 595, 597, 599, 600, 602, 603, 604, 605, 606, 608], "branches": [[590, 591], [592, 593], [594, 595], [599, 600], [602, 603]]}

import pytest

from aider.coders import search_replace as sr


def test_try_strategy_all_preprocs_success(monkeypatch):
    calls = {
        "strip": 0,
        "relative": 0,
        "reverse": 0,
        "strategy": 0,
        "make_absolute": 0,
    }

    # original texts
    texts_in = [" line1", "", "line2"]

    # patch strip_blank_lines to remove empty strings and strip whitespace
    def fake_strip_blank_lines(texts):
        calls["strip"] += 1
        # emulate removing blank lines and stripping
        return [t.strip() for t in texts if t.strip()]

    monkeypatch.setattr(sr, "strip_blank_lines", fake_strip_blank_lines)

    # patch relative_indent to return a ri object and (possibly modified) texts
    class RI:
        def make_absolute(self, s):
            calls["make_absolute"] += 1
            return "MA:" + s

    def fake_relative_indent(texts):
        calls["relative"] += 1
        # no change to texts, return RI instance
        return RI(), texts

    monkeypatch.setattr(sr, "relative_indent", fake_relative_indent)

    # patch reverse_lines to reverse strings
    def fake_reverse_lines(s):
        calls["reverse"] += 1
        return s[::-1]

    monkeypatch.setattr(sr, "reverse_lines", fake_reverse_lines)

    # strategy joins the texts with '|'
    def strategy(texts):
        calls["strategy"] += 1
        # Expect to receive reversed individual lines because preproc_reverse will run
        return "|".join(texts)

    # run with all preproc flags True
    preproc = (True, True, True)
    res = sr.try_strategy(list(texts_in), strategy, preproc)

    # Build expected result:
    # 1) strip_blank_lines -> ["line1", "line2"]
    stripped = ["line1", "line2"]
    # 2) relative_indent returns same texts
    # 3) reverse_lines applied to each => ["1enil", "2enil"]
    reversed_each = [s[::-1] for s in stripped]
    # 4) strategy returns "1enil|2enil"
    strat = "|".join(reversed_each)
    # 5) res is then reversed (entire string) => strat[::-1]
    reversed_entire = strat[::-1]
    # 6) ri.make_absolute prepends "MA:"
    expected = "MA:" + reversed_entire

    assert res == expected
    # verify the patched functions were called at least once each
    assert calls["strip"] == 1
    assert calls["relative"] == 1
    # reverse_lines called for each element plus once for the final result:
    # two elements + one final reverse => 3
    assert calls["reverse"] == len(stripped) + 1
    assert calls["strategy"] == 1
    assert calls["make_absolute"] == 1


def test_try_strategy_make_absolute_raises_returns_none(monkeypatch):
    calls = {
        "strip": 0,
        "relative": 0,
        "reverse": 0,
        "strategy": 0,
        "make_absolute": 0,
    }

    texts_in = ["a", "b"]

    def fake_strip_blank_lines(texts):
        calls["strip"] += 1
        return texts

    monkeypatch.setattr(sr, "strip_blank_lines", fake_strip_blank_lines)

    class RI:
        def make_absolute(self, s):
            calls["make_absolute"] += 1
            raise ValueError("cannot make absolute")

    def fake_relative_indent(texts):
        calls["relative"] += 1
        return RI(), texts

    monkeypatch.setattr(sr, "relative_indent", fake_relative_indent)

    def fake_reverse_lines(s):
        calls["reverse"] += 1
        return s[::-1]

    monkeypatch.setattr(sr, "reverse_lines", fake_reverse_lines)

    def strategy(texts):
        calls["strategy"] += 1
        # return a truthy result so that make_absolute will be called and raise
        return "result"

    preproc = (True, True, True)
    res = sr.try_strategy(list(texts_in), strategy, preproc)

    # When make_absolute raises ValueError, try_strategy returns None
    assert res is None

    assert calls["strip"] == 1
    assert calls["relative"] == 1
    # reverse_lines called for each element in texts before strategy,
    # plus it could be called on the strategy result before make_absolute.
    # Ensure it was called at least once.
    assert calls["reverse"] >= 1
    assert calls["strategy"] == 1
    assert calls["make_absolute"] == 1
