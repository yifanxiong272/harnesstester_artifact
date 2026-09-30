# file: aider/coders/search_replace.py:193-226
# asked: {"lines": [194, 196, 197, 199, 205, 206, 207, 209, 210, 212, 213, 214, 216, 217, 219, 220, 221, 222, 223, 224, 226], "branches": [[205, 206], [205, 212], [212, 213], [212, 226], [219, 212], [219, 220]]}
# gained: {"lines": [194, 196, 197, 199, 205, 206, 207, 209, 210, 212, 213, 214, 216, 217, 219, 220, 221, 222, 223, 224, 226], "branches": [[205, 206], [205, 212], [212, 213], [212, 226], [219, 212], [219, 220]]}

import builtins
import types
from pathlib import Path

import pytest

import aider.coders.search_replace as search_replace


class FakeDMP:
    def __init__(self):
        # allow assignment to Diff_Timeout as in real object
        self.Diff_Timeout = None
        # store last diff passed to prettyHtml for verification
        self._last_diff = None

    def diff_main(self, a, b):
        # Return a simple diff structure; real diff_main returns list of tuples,
        # but our diff_xIndex only needs to receive it back unchanged.
        diff = [("EQUAL", a), ("SEPARATOR", b)]
        self._last_diff = diff
        return diff

    def diff_prettyHtml(self, diff):
        # Return deterministic HTML that includes lengths for assertions
        return f"<html>DIFF len={len(diff)}></html>"

    def diff_xIndex(self, diff, index):
        # Simple, deterministic mapping for index translation: add 1
        return index + 1


class SimplePatch:
    def __init__(self, start1, start2, diffs):
        self.start1 = start1
        self.start2 = start2
        self.diffs = diffs

    def __repr__(self):
        return f"SimplePatch(start1={self.start1}, start2={self.start2}, diffs={self.diffs})"


def test_map_patches_with_debug_true(monkeypatch, capsys, tmp_path):
    # Arrange
    # Replace diff_match_patch in the module with our FakeDMP
    monkeypatch.setattr(search_replace, "diff_match_patch", FakeDMP)

    # Capture calls to dump
    dump_calls = []

    def fake_dump(arg):
        dump_calls.append(arg)

    monkeypatch.setattr(search_replace, "dump", fake_dump)

    # Capture calls to Path.write_text; ensure no real file is left behind
    write_calls = []

    original_write_text = Path.write_text

    def fake_write_text(self, data, *args, **kwargs):
        # Record the path and contents
        write_calls.append((str(self), data))
        # emulate actual write by creating file in tmp_path if requested
        # but do not rely on actual content later
        return len(data)

    monkeypatch.setattr(Path, "write_text", fake_write_text)

    # Prepare texts such that slicing in debug prints stays within bounds
    search_text = "abcdefghijklmnopqrstuvwxyz"  # length 26
    replace_text = "REPL"
    original_text = "XX" + search_text + "YY"  # ensure original contains search_text in offset 2

    # Single patch with starts that will be remapped by diff_xIndex (+1)
    p = SimplePatch(start1=2, start2=3, diffs=[("EQUAL", "abc")])

    # Act
    out = search_replace.map_patches(
        texts=(search_text, replace_text, original_text), patches=[p], debug=True
    )

    # Capture printed output
    captured = capsys.readouterr()

    # Assert
    # map_patches should return the same patch objects list with updated starts (+1)
    assert isinstance(out, list) and out, "Expected non-empty list of patches returned"
    returned_patch = out[0]
    assert returned_patch.start1 == 3, "start1 should have been incremented by FakeDMP.diff_xIndex"
    assert returned_patch.start2 == 4, "start2 should have been incremented by FakeDMP.diff_xIndex"

    # Path.write_text should have been called once with HTML from FakeDMP
    assert write_calls, "Expected Path.write_text to be called when debug=True"
    path_str, html = write_calls[0]
    assert "DIFF len=" in html and html.startswith("<html>"), "Expected HTML from fake diff_prettyHtml"

    # dump should have been called twice with lengths of search_text and original_text
    assert dump_calls == [len(search_text), len(original_text)]

    # Printed output should include the original start1 and the repr of the sliced texts and diffs
    assert str(2) in captured.out  # original start1 printed
    assert "repr" not in captured.out  # ensure actual repr content printed, not the literal word
    assert "('EQUAL', 'abc')" in captured.out or "('EQUAL', 'abc')" in repr(returned_patch.diffs)

    # Cleanup: monkeypatch will revert Path.write_text and other attributes


def test_map_patches_with_debug_false(monkeypatch, capsys):
    # Arrange
    monkeypatch.setattr(search_replace, "diff_match_patch", FakeDMP)

    # Replace dump and Path.write_text to detect that they are NOT called
    dump_calls = []

    def fake_dump(arg):
        dump_calls.append(arg)

    monkeypatch.setattr(search_replace, "dump", fake_dump)

    write_calls = []

    def fake_write_text(self, data, *args, **kwargs):
        write_calls.append((str(self), data))
        return len(data)

    monkeypatch.setattr(Path, "write_text", fake_write_text)

    # texts and patch
    search_text = "hello world"
    replace_text = "hi"
    original_text = "xxhello worldyy"

    p1 = SimplePatch(start1=0, start2=5, diffs=[("DELETE", "h"), ("INSERT", "H")])
    p2 = SimplePatch(start1=4, start2=7, diffs=[("EQUAL", "o w")])

    patches = [p1, p2]

    # Act
    out = search_replace.map_patches(
        texts=(search_text, replace_text, original_text), patches=patches, debug=False
    )

    # There should be no writes or dumps when debug is False
    assert write_calls == [], "Path.write_text should not be called when debug=False"
    assert dump_calls == [], "dump should not be called when debug=False"

    # But the patch start indices should still be updated by fake diff_xIndex (+1)
    assert out[0].start1 == 1
    assert out[0].start2 == 6
    assert out[1].start1 == 5
    assert out[1].start2 == 8

    # Also no printing should have occurred
    captured = capsys.readouterr()
    assert captured.out == ""
