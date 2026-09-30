import importlib
import pytest

import aider.coders.search_replace as sr


class FakeDMP:
    def __init__(self, success_all=True, new_lines=None):
        self.success_all = success_all
        # new_lines should be a list of line strings (with newlines if desired)
        self.new_lines = new_lines if new_lines is not None else ["X\n"]

    def diff_linesToChars(self, all_text, _):
        # Return a list whose length matches the number of lines in all_text
        lines = all_text.splitlines()
        # The real function returns (all_lines, _, mapping). We return a simple mapping.
        return list(lines), None, {"mapping": lines}

    def diff_main(self, a, b, _):
        # Return a benign diff structure; code under test only passes it through cleanup.
        return [(0, a), (1, b)]

    def diff_cleanupSemantic(self, diff_lines):
        return None

    def diff_cleanupEfficiency(self, diff_lines):
        return None

    def patch_make(self, search_lines, diff_lines):
        # Return a placeholder patches object
        return ["patch"]

    def patch_apply(self, patches, original_lines):
        # Return deterministic new_lines and a success list depending on configuration
        if self.success_all:
            return self.new_lines, [True] * len(self.new_lines)
        else:
            # include at least one False to exercise the failure branch
            return self.new_lines, [False]


def setup_fake(monkeypatch, success_all=True, new_lines=None):
    # Patch the symbol as it is resolved in the module under test
    monkeypatch.setattr(sr, "diff_match_patch", lambda: FakeDMP(success_all=success_all, new_lines=new_lines))
    # Patch lines_to_chars so the function can deterministically produce text from new_lines
    monkeypatch.setattr(sr, "lines_to_chars", lambda new_lines, mapping: "".join(new_lines))


def test_dmp_lines_apply_success_round_013(monkeypatch):
    """When patch_apply indicates full success, the function should return the reconstructed text."""
    setup_fake(monkeypatch, success_all=True, new_lines=["result\n"])
    texts = ["search\n", "replace\n", "orig\n"]

    res = sr.dmp_lines_apply(texts)

    assert res == "result\n"


def test_dmp_lines_apply_partial_failure_round_013(monkeypatch):
    """When patch_apply reports a failure (contains False) the function should return None."""
    setup_fake(monkeypatch, success_all=False, new_lines=["ignored\n"])
    texts = ["s\n", "r\n", "o\n"]

    res = sr.dmp_lines_apply(texts)

    assert res is None


def test_dmp_lines_apply_assert_bad_line_round_013(monkeypatch):
    """If any input line does not end with a newline an AssertionError should be raised and include the bad line."""
    # Use a valid fake to avoid reaching deeper code paths before the assertion
    setup_fake(monkeypatch, success_all=True)
    texts = ["a\n", "badline", "c\n"]

    with pytest.raises(AssertionError) as exc:
        sr.dmp_lines_apply(texts)

    # The assertion message is the offending line according to the code under test
    assert "badline" in str(exc.value)
