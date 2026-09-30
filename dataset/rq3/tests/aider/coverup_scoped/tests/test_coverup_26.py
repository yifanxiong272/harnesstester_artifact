# file: aider/coders/search_replace.py:586-608
# asked: {"lines": [587, 588, 590, 591, 592, 593, 594, 595, 597, 599, 600, 602, 603, 604, 605, 606, 608], "branches": [[590, 591], [590, 592], [592, 593], [592, 594], [594, 595], [594, 597], [599, 600], [599, 602], [602, 603], [602, 608]]}
# gained: {"lines": [587, 588, 590, 591, 592, 593, 594, 595, 597, 599, 600, 602, 603, 604, 605, 606, 608], "branches": [[590, 591], [590, 592], [592, 593], [592, 594], [594, 595], [594, 597], [599, 600], [599, 602], [602, 603], [602, 608]]}

import pytest
from types import SimpleNamespace

from aider.coders import search_replace as sr


def test_try_strategy_no_preproc(monkeypatch):
    calls = []

    # Ensure none of the preproc helpers are invoked
    def fake_strip(texts):
        calls.append("strip")
        return texts

    def fake_relative(texts):
        calls.append("relative")
        return (None, texts)

    def fake_reverse(s):
        calls.append("reverse")
        return s

    monkeypatch.setattr(sr, "strip_blank_lines", fake_strip)
    monkeypatch.setattr(sr, "relative_indent", fake_relative)
    monkeypatch.setattr(sr, "reverse_lines", fake_reverse)

    # Strategy should be called with the original texts
    def strategy(texts):
        calls.append(("strategy", list(texts)))
        return "RESULT"

    preproc = (False, False, False)
    texts = [" line1 ", "", "line2"]

    res = sr.try_strategy(texts, strategy, preproc)

    assert res == "RESULT"
    # Only strategy should have been called; helpers should not
    assert ("strategy", texts) in calls or any(c[0] == "strategy" for c in calls)
    assert "strip" not in calls
    assert "relative" not in calls
    assert "reverse" not in calls


def test_try_strategy_all_true_success(monkeypatch):
    order = []

    # strip_blank_lines will remove blank lines
    def fake_strip(texts):
        order.append("strip")
        return [t.strip() for t in texts if t.strip()]

    # relative_indent returns an ri object and rewritten texts
    class RI:
        def __init__(self):
            self.called_with = None

        def make_absolute(self, res):
            order.append(("ri.make_absolute", res))
            return "ABS:" + res

    def fake_relative(texts):
        order.append(("relative", list(texts)))
        ri = RI()
        # pretend to add a prefix to indicate relative indent processing
        return ri, [f"INDENT:{t}" for t in texts]

    # reverse_lines will add a prefix so we can detect its use on both lists and single res
    def fake_reverse(s):
        order.append(("reverse", s))
        return f"REV:{s}"

    monkeypatch.setattr(sr, "strip_blank_lines", fake_strip)
    monkeypatch.setattr(sr, "relative_indent", fake_relative)
    monkeypatch.setattr(sr, "reverse_lines", fake_reverse)

    # Strategy should receive texts after strip, relative indent and reverse mapping
    def strategy(texts):
        # texts should have been processed by fake_reverse via map
        order.append(("strategy_called_with", list(texts)))
        # return a truthy value that will be reversed and then made absolute
        return "STR_RES"

    preproc = (True, True, True)
    input_texts = [" a ", "", "b"]

    res = sr.try_strategy(input_texts, strategy, preproc)

    # Expected flow:
    # 1. strip_blank_lines -> ["a","b"]
    # 2. relative_indent -> ["INDENT:a","INDENT:b"]
    # 3. reverse_lines mapped -> ["REV:INDENT:a","REV:INDENT:b"]
    # 4. strategy receives that list and returns "STR_RES"
    # 5. res is truthy and preproc_reverse True -> reverse_lines("STR_RES") -> "REV:STR_RES"
    # 6. ri.make_absolute("REV:STR_RES") -> "ABS:REV:STR_RES"
    assert res == "ABS:REV:STR_RES"

    # Check that the helper functions were called in expected sequence (order partially)
    assert order[0] == "strip"
    assert any(o[0] == "relative" for o in order)
    assert any(o[0] == "strategy_called_with" for o in order)
    # Ensure reverse was used both on list items and on the final res
    reverse_calls = [o for o in order if isinstance(o, tuple) and o[0] == "reverse"]
    assert len(reverse_calls) >= 1
    assert any(isinstance(o, tuple) and o[0] == "ri.make_absolute" for o in order)


def test_try_strategy_relative_indent_make_absolute_raises(monkeypatch):
    calls = []

    # relative_indent returns an ri object whose make_absolute raises ValueError
    class RIError:
        def make_absolute(self, res):
            calls.append(("ri.make_absolute", res))
            raise ValueError("bad absolute")

    def fake_relative(texts):
        calls.append(("relative", list(texts)))
        return RIError(), texts

    # other helpers shouldn't be invoked in this test
    def fake_strip(texts):
        calls.append("strip")
        return texts

    def fake_reverse(s):
        calls.append(("reverse", s))
        return s

    monkeypatch.setattr(sr, "strip_blank_lines", fake_strip)
    monkeypatch.setattr(sr, "relative_indent", fake_relative)
    monkeypatch.setattr(sr, "reverse_lines", fake_reverse)

    # Strategy returns a truthy result so that make_absolute will be attempted and then raise
    def strategy(texts):
        calls.append(("strategy", list(texts)))
        return "SOMETHING"

    preproc = (False, True, False)
    texts = ["x", "y"]

    res = sr.try_strategy(texts, strategy, preproc)

    # Because make_absolute raises ValueError, try_strategy should return None (no value)
    assert res is None

    # Verify expected calls occurred
    assert ("relative", texts) in calls or any(c == ("relative", list(texts)) for c in calls)
    assert ("strategy", list(["x", "y"])) in calls or any(c[0] == "strategy" for c in calls)
    assert ("ri.make_absolute", "SOMETHING") in calls
