# file: aider/coders/udiff_coder.py:69-118
# asked: {"lines": [73, 74, 75, 77, 78, 80, 81, 82, 84, 88, 89, 91, 93, 94, 95, 96, 97, 98, 101, 103, 104, 105, 106, 109, 112, 115, 116, 117, 118], "branches": [[72, 73], [74, 75], [74, 77], [80, 81], [80, 82], [87, 88], [103, 104], [103, 112], [114, 115], [116, 117], [116, 118]]}
# gained: {"lines": [73, 74, 75, 77, 78, 80, 81, 82, 84, 88, 89, 91, 93, 94, 95, 96, 97, 98, 101, 103, 104, 105, 106, 109, 112, 115, 116, 118], "branches": [[72, 73], [74, 75], [74, 77], [80, 81], [80, 82], [87, 88], [103, 104], [103, 112], [114, 115], [116, 118]]}

import os
import pathlib
import pytest

import aider.coders.udiff_coder as udiff


class SimpleIO:
    def __init__(self):
        self.writes = []
        self.encoding = "utf-8"
        self.pretty = False

    def read_text(self, full_path):
        p = pathlib.Path(full_path)
        return p.read_text()

    def write_text(self, full_path, content):
        p = pathlib.Path(full_path)
        p.write_text(content)
        self.writes.append((str(full_path), content))


def make_coder_with_io(tmp_path):
    # Avoid calling Coder.__init__ which requires heavy setup; create instance and set minimal attrs
    coder = object.__new__(udiff.UnifiedDiffCoder)
    coder.io = SimpleIO()
    coder.abs_root_path = lambda path: str(pathlib.Path(tmp_path) / path)
    return coder


def _normalize_hunk_passthrough(hunk):
    if any(line == "EMPTY" for line in hunk):
        return []
    return hunk


def test_apply_edits_writes_and_dedup_and_skips_empty(monkeypatch, tmp_path):
    # Prepare file
    fpath = tmp_path / "a.txt"
    fpath.write_text("orig\n")
    coder = make_coder_with_io(tmp_path)

    # Monkeypatch normalize_hunk to skip hunks containing "EMPTY"
    monkeypatch.setattr(udiff, "normalize_hunk", _normalize_hunk_passthrough)

    # Track calls to do_replace and force it to return a new content
    calls = {"count": 0}

    def fake_do_replace(full_path, content, hunk):
        calls["count"] += 1
        before, after = udiff.hunk_to_before_after(hunk)
        return after

    monkeypatch.setattr(udiff, "do_replace", fake_do_replace)

    # Two identical hunks (should be deduped -> only one write), plus one empty hunk (skipped)
    hunk = [" orig\n", "-orig\n", "+new\n"]
    edits = [
        ("a.txt", ["EMPTY"]),  # will be normalized to [], should be skipped
        ("a.txt", hunk),
        ("a.txt", hunk),  # duplicate; should be deduped
    ]

    coder.apply_edits(edits)

    # Only one actual write should have occurred
    assert len(coder.io.writes) == 1
    written_path, written_content = coder.io.writes[0]
    assert os.path.basename(written_path) == "a.txt"
    # The expected content is the 'after' produced by hunk_to_before_after for the hunk:
    assert written_content == "orig\nnew\n"
    # do_replace should have been called once (deduped)
    assert calls["count"] == 1
    # file actual content should have been updated
    assert fpath.read_text() == "orig\nnew\n"


def test_apply_edits_search_text_not_unique_produces_valueerror_with_note(monkeypatch, tmp_path):
    # Create two files so we have multiple hunks
    (tmp_path / "f1.txt").write_text("content1\n")
    (tmp_path / "f2.txt").write_text("content2\n")

    coder = make_coder_with_io(tmp_path)

    # normalize_hunk passthrough
    monkeypatch.setattr(udiff, "normalize_hunk", lambda h: h)

    # make do_replace always raise SearchTextNotUnique
    from aider.coders.search_replace import SearchTextNotUnique

    def raise_not_unique(full_path, content, hunk):
        raise SearchTextNotUnique()

    monkeypatch.setattr(udiff, "do_replace", raise_not_unique)

    edits = [
        ("f1.txt", [" line\n", "-a\n", "+b\n"]),
        ("f2.txt", [" other\n", "-x\n", "+y\n"]),
    ]

    with pytest.raises(ValueError) as excinfo:
        coder.apply_edits(edits)

    msg = str(excinfo.value)
    # Should mention UnifiedDiffNotUnique message text
    assert "UnifiedDiffNotUnique" in msg


def test_apply_edits_no_match_error_appended_and_valueerror(monkeypatch, tmp_path):
    # Create one file
    (tmp_path / "g.txt").write_text("AAA\n")

    coder = make_coder_with_io(tmp_path)
    monkeypatch.setattr(udiff, "normalize_hunk", lambda h: h)

    # do_replace returns None to simulate no match -> triggers no_match_error branch
    def return_none(full_path, content, hunk):
        return None

    monkeypatch.setattr(udiff, "do_replace", return_none)

    edits = [
        ("g.txt", [" AAA\n", "-old\n", "+new\n"]),
    ]

    with pytest.raises(ValueError) as excinfo:
        coder.apply_edits(edits)

    msg = str(excinfo.value)
    assert "UnifiedDiffNoMatch" in msg
