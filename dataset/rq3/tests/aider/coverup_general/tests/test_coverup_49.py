# file: aider/coders/udiff_coder.py:121-144
# asked: {"lines": [122, 124, 127, 128, 129, 131, 132, 135, 137, 138, 140, 142, 143, 144], "branches": [[127, 128], [127, 131], [131, 132], [131, 135], [135, 137], [135, 140], [143, 0], [143, 144]]}
# gained: {"lines": [122, 124, 127, 128, 129, 131, 132, 135, 137, 138, 140, 142, 143, 144], "branches": [[127, 128], [127, 131], [131, 132], [131, 135], [135, 137], [135, 140], [143, 0], [143, 144]]}

import os
from pathlib import Path
import pytest

from aider.coders import udiff_coder as uc


def test_do_replace_new_file_and_append(monkeypatch, tmp_path):
    # Arrange: make sure path does not exist
    fname = tmp_path / "newfile.txt"
    assert not fname.exists()

    # Patch hunk_to_before_after to indicate an empty before_text and some after_text
    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: ("", "AFTER\n"))

    # apply_hunk should not be called in this scenario, but patch defensively
    monkeypatch.setattr(uc, "apply_hunk", lambda content, hunk: "SHOULD_NOT_BE_USED")

    # Act: content arg can be None - function will create the file and set content = ''
    result = uc.do_replace(str(fname), None, hunk="dummy")

    # Assert: function returns appended after_text, file is created and empty
    assert result == "AFTER\n"
    assert fname.exists()
    # The function only touches the file and does not write content to it
    assert fname.read_text() == ""


def test_do_replace_existing_file_before_nonempty_content_none_returns_none(monkeypatch, tmp_path):
    # Arrange: create the file so the "create file" branch is not executed
    fname = tmp_path / "exists.txt"
    fname.write_text("existing")
    assert fname.exists()

    # Patch hunk_to_before_after to return non-empty before_text
    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: ("SOME BEFORE", "AFTER"))

    # Patch apply_hunk to raise if called (it should not be when content is None, since function returns early)
    called = {"apply_called": False}
    def fake_apply(content, hunk):
        called["apply_called"] = True
        return "SHOULD_NOT_BE_USED"
    monkeypatch.setattr(uc, "apply_hunk", fake_apply)

    # Act: pass content as None -> should return None
    result = uc.do_replace(str(fname), None, hunk="dummy")

    # Assert: returns None and apply_hunk was not called
    assert result is None
    assert called["apply_called"] is False


def test_do_replace_before_empty_append_existing_file(monkeypatch, tmp_path):
    # Arrange: create the file so exists() is True
    fname = tmp_path / "exists2.txt"
    fname.write_text("original")
    assert fname.exists()

    # Patch hunk_to_before_after to indicate empty before_text and some after_text
    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: ("", "\nAPPENDED"))

    # apply_hunk should not be used here
    monkeypatch.setattr(uc, "apply_hunk", lambda content, hunk: "SHOULD_NOT_BE_USED")

    # Act: pass a non-None content, expect append behavior
    result = uc.do_replace(str(fname), "original", hunk="dummy")

    # Assert: returned content is original + after_text
    assert result == "original\nAPPENDED"


def test_do_replace_apply_hunk_called_and_results(monkeypatch):
    # Arrange: patch hunk_to_before_after to have non-empty before_text to force apply_hunk usage
    monkeypatch.setattr(uc, "hunk_to_before_after", lambda h: ("SOME BEFORE", "AFTER"))

    # Case A: apply_hunk returns a truthy value -> should be returned
    monkeypatch.setattr(uc, "apply_hunk", lambda content, hunk: "NEW_CONTENT")
    res = uc.do_replace("irrelevant_path.txt", "OLD_CONTENT", hunk="h")
    assert res == "NEW_CONTENT"

    # Case B: apply_hunk returns None/falsy -> do_replace should return None
    monkeypatch.setattr(uc, "apply_hunk", lambda content, hunk: None)
    res2 = uc.do_replace("irrelevant_path.txt", "OLD_CONTENT", hunk="h")
    assert res2 is None

    # Case C: apply_hunk returns empty string (falsy) -> do_replace should return None
    monkeypatch.setattr(uc, "apply_hunk", lambda content, hunk: "")
    res3 = uc.do_replace("irrelevant_path.txt", "OLD_CONTENT", hunk="h")
    assert res3 is None
