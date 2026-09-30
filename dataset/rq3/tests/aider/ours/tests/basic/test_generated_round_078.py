import importlib
import pytest


def test_touch_and_set_content_round_078(tmp_path, monkeypatch):
    """
    Exercise the branch where the target file does not exist and the hunk's
    before_text is empty. The function should touch the file, reset content to
    an empty string, then return the appended after_text.
    """
    mod = importlib.import_module("aider.coders.udiff_coder")

    # Make hunk_to_before_after deterministic: empty before_text triggers the
    # 'new file' branch and the append branch.
    monkeypatch.setattr(mod, "hunk_to_before_after", lambda h: ("", "AFTERTEXT"))

    fname = tmp_path / "newfile.txt"
    assert not fname.exists()

    # Provide a non-None content value; code path should override it to "" when
    # file doesn't exist and before_text is empty.
    result = mod.do_replace(str(fname), "ORIG_CONTENT", {"dummy": "hunk"})

    # Expect append behavior: content was set to "" and after_text appended.
    assert result == "AFTERTEXT"

    # File should have been touched (created) but remain empty because do_replace
    # does not write content to disk after touch.
    assert fname.exists()
    assert fname.read_text() == ""


def test_content_none_returns_none_round_078(monkeypatch):
    """
    When content is None, do_replace should return None immediately after
    computing before/after context. This ensures the early-return branch is
    covered.
    """
    mod = importlib.import_module("aider.coders.udiff_coder")

    # Ensure hunk_to_before_after is present and deterministic; not important
    # for this test except to avoid side effects.
    monkeypatch.setattr(mod, "hunk_to_before_after", lambda h: ("before", "after"))

    res = mod.do_replace("somefile.txt", None, {"h": "x"})
    assert res is None


def test_apply_hunk_returned_used_round_078(monkeypatch):
    """
    Cover the path where before_text is non-empty so apply_hunk is invoked.
    Patch apply_hunk to return a truthy new_content and assert that it is
    returned by do_replace and that apply_hunk received the original args.
    """
    mod = importlib.import_module("aider.coders.udiff_coder")

    # before_text non-empty to force the apply_hunk path
    monkeypatch.setattr(mod, "hunk_to_before_after", lambda h: ("some_before", "some_after"))

    called = {}

    def fake_apply_hunk(content, hunk):
        # capture arguments to assert they were forwarded unchanged
        called['args'] = (content, hunk)
        return "NEW_CONTENT"

    monkeypatch.setattr(mod, "apply_hunk", fake_apply_hunk)

    sample_hunk = {"h": "x"}
    res = mod.do_replace("irrelevant_path.txt", "OLD_CONTENT", sample_hunk)

    assert res == "NEW_CONTENT"
    assert called['args'] == ("OLD_CONTENT", sample_hunk)
