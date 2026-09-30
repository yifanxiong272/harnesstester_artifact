import pytest
from aider.coders import search_replace as sr


class FakeDMP:
    """A minimal fake of diff_match_patch.diff_match_patch to control behavior deterministically."""
    def __init__(self):
        # map the attribute that the code under test sets
        self.Diff_Timeout = None

    def diff_main(self, a, b):
        # Return a harmless diff structure; the implementation under test
        # only passes this value to diff_xIndex and diff_prettyHtml.
        return [(0, a, b)]

    def diff_prettyHtml(self, diff):
        return "<html_preview>"

    def diff_xIndex(self, diff, index):
        # deterministically map indexes: +1 for tests
        return index + 1


class Patch:
    def __init__(self, start1, start2, diffs):
        self.start1 = start1
        self.start2 = start2
        self.diffs = diffs


def test_map_patches_debug_true_round_064(monkeypatch, capsys):
    """Exercise the debug=True branch: html should be written, dump called,
    start indexes remapped, and verbose prints emitted.
    """
    # Patch the constructor used in the module under test
    monkeypatch.setattr(sr, "diff_match_patch", lambda: FakeDMP())

    # Capture calls to Path.write_text without touching the filesystem
    written = {}

    def fake_write_text(self, content):
        written["content"] = content

    monkeypatch.setattr(sr.Path, "write_text", fake_write_text, raising=False)

    # Capture dumps (should be called twice: len(search_text), len(original_text))
    dump_calls = []

    def fake_dump(value):
        dump_calls.append(value)

    monkeypatch.setattr(sr, "dump", fake_dump)

    search_text = "hello world"
    replace_text = "REPLACE"
    original_text = "Xhello world"

    texts = (search_text, replace_text, original_text)
    p = Patch(start1=1, start2=2, diffs=[("=", "chunk")])

    out = sr.map_patches(texts, [p], debug=True)

    # Confirm html generation was invoked and captured
    assert written.get("content") == "<html_preview>"

    # dump should have been called twice with the lengths of search and original
    assert dump_calls == [len(search_text), len(original_text)]

    # The patch object's start indices should be updated consistently by diff_xIndex
    assert out[0].start1 == 2  # original 1 + 1
    assert out[0].start2 == 3  # original 2 + 1

    # The debug branch emits prints; ensure they include expected slices/values
    captured = capsys.readouterr().out
    assert "1" in captured  # original start1 printed
    assert repr(search_text[1:1 + 50]) in captured
    # printed patched start1 should correspond to updated value
    assert repr(original_text[2:2 + 50]) in captured


def test_map_patches_debug_false_round_064(monkeypatch, capsys):
    """Exercise the debug=False branch: no html/dump/prints but indexes still remapped.
    """
    monkeypatch.setattr(sr, "diff_match_patch", lambda: FakeDMP())

    # If Path.write_text or dump are called in this scenario, fail the test.
    def fail_write(self, content):
        raise AssertionError("write_text was unexpectedly called")

    monkeypatch.setattr(sr.Path, "write_text", fail_write, raising=False)

    def fail_dump(value):
        raise AssertionError("dump was unexpectedly called")

    monkeypatch.setattr(sr, "dump", fail_dump)

    search_text = "abcdef"
    replace_text = "REPL"
    original_text = "Zabcdef"

    texts = (search_text, replace_text, original_text)
    p = Patch(start1=0, start2=1, diffs=[("=", "x")])

    out = sr.map_patches(texts, [p], debug=False)

    # Index remapping still happens even when debug is False
    assert out[0].start1 == 1
    assert out[0].start2 == 2

    # No debug prints should have been emitted
    captured = capsys.readouterr().out
    assert captured == ""
