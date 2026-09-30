import importlib
import pytest

sr = importlib.import_module("aider.coders.search_replace")


def test_strip_blank_lines_applied_round_065(monkeypatch):
    # Ensure strip_blank_lines is applied and strategy receives the stripped texts
    called = {}

    def fake_strip_blank_lines(texts):
        # record input and return a deterministic stripped list
        called['strip_in'] = list(texts)
        return [t for t in texts if t != ""]

    monkeypatch.setattr(sr, 'strip_blank_lines', fake_strip_blank_lines)

    def strategy(obtained_texts):
        called['strategy_arg'] = list(obtained_texts)
        return "OK"

    res = sr.try_strategy(["a", "", "b"], strategy, (True, False, False))

    assert called['strip_in'] == ["a", "", "b"]
    assert called['strategy_arg'] == ["a", "b"]
    assert res == "OK"


def test_relative_indent_make_absolute_success_round_065(monkeypatch):
    # Ensure relative_indent produces an ri used to make_absolute on the strategy result
    class RI:
        def make_absolute(self, res):
            return "ABS:" + res

    def fake_relative_indent(texts):
        # transform texts so we can assert the strategy saw modified values
        return (RI(), ["r-" + t for t in texts])

    monkeypatch.setattr(sr, 'relative_indent', fake_relative_indent)

    seen = {}

    def strategy(texts):
        seen['texts'] = list(texts)
        return "RESULT"

    res = sr.try_strategy(["x", "y"], strategy, (False, True, False))

    assert seen['texts'] == ["r-x", "r-y"]
    assert res == "ABS:RESULT"


def test_reverse_pre_and_post_round_065(monkeypatch):
    # reverse_lines should be applied to each input text during preproc and to the result after strategy
    def fake_reverse(s):
        return f"REV[{s}]"

    monkeypatch.setattr(sr, 'reverse_lines', fake_reverse)

    seen = {}

    def strategy(texts):
        seen['texts'] = list(texts)
        return "RET"

    res = sr.try_strategy(["a"], strategy, (False, False, True))

    assert seen['texts'] == ["REV[a]"]
    assert res == "REV[RET]"


def test_make_absolute_valueerror_returns_none_round_065(monkeypatch):
    # If ri.make_absolute raises ValueError, try_strategy should catch it and return None
    class RI:
        def make_absolute(self, res):
            raise ValueError("bad absolute")

    def fake_relative_indent(texts):
        return (RI(), ["x"])

    monkeypatch.setattr(sr, 'relative_indent', fake_relative_indent)

    def strategy(texts):
        # strategy returns a truthy value so the code attempts make_absolute
        return "WILL_FAIL"

    res = sr.try_strategy(["a"], strategy, (False, True, False))

    assert res is None
