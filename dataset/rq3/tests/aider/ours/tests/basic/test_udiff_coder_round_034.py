import types
import pytest
from types import SimpleNamespace

from aider.coders import udiff_coder as udiff

class FakeSearchTextNotUnique(Exception):
    pass


def make_self(write_calls):
    """
    Create a fake `self` object with abs_root_path and io attributes used by apply_edits.
    write_calls: list to append (path, content) tuples when write_text is called.
    """
    def abs_root_path(p):
        return "/abs/" + p

    def read_text(p):
        # content read is not used for logic checks besides being passed to do_replace
        return "original file content"

    def write_text(p, content):
        write_calls.append((p, content))

    io = SimpleNamespace(read_text=read_text, write_text=write_text)
    return SimpleNamespace(abs_root_path=abs_root_path, io=io)


def test_success_dedup_round_034(monkeypatch):
    """
    Two identical edits should be deduplicated; do_replace returns content and
    write_text should be called exactly once for the deduplicated hunk.
    Covers: normalize_hunk path, seen/duplicate skip, successful write (lines 72-84, 111-112)
    """
    # Make normalize_hunk return the hunk unchanged
    monkeypatch.setattr(udiff, "normalize_hunk", lambda h: h)

    # hunk_to_before_after not needed for this success path, but provide a stub
    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: ("orig", "after"))

    # do_replace returns new content for any path
    def do_replace_ok(full_path, content, hunk):
        return "NEW_CONTENT"

    monkeypatch.setattr(udiff, "do_replace", do_replace_ok)

    # Ensure error message templates exist (not used in this test)
    monkeypatch.setattr(udiff, "not_unique_error", "NOTUNIQUE:{path}:{original}:{num_lines}")
    monkeypatch.setattr(udiff, "no_match_error", "NOMATCH:{path}:{original}:{num_lines}")
    monkeypatch.setattr(udiff, "other_hunks_applied", "<OTHER_APPLIED>")
    monkeypatch.setattr(udiff, "SearchTextNotUnique", FakeSearchTextNotUnique)

    write_calls = []
    self = make_self(write_calls)

    # Two identical edits (same path and identical hunk contents)
    edits = [("file.txt", ["line1\n"]), ("file.txt", ["line1\n"])]

    # Call the function under test (unbound function call with our fake self)
    udiff.UnifiedDiffCoder.apply_edits(self, edits)

    # Exactly one write should have occurred for the deduplicated hunks
    assert len(write_calls) == 1
    assert write_calls[0][0] == "/abs/file.txt"
    assert write_calls[0][1] == "NEW_CONTENT"


def test_errors_with_other_hunks_appended_round_034(monkeypatch):
    """
    Create multiple hunks where one raises SearchTextNotUnique and another returns
    an empty string (no match). There are multiple hunks in uniq so the string-length
    comparison (len(errors) < len(uniq)) should be True and other_hunks_applied appended.
    This exercises the SearchTextNotUnique except branch, no-match branch, and
    the 'append other_hunks_applied' branch (lines 93-101, 103-109, 114-118).
    """
    # Use identity normalizer and a simple before/after extractor
    monkeypatch.setattr(udiff, "normalize_hunk", lambda h: h)
    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: ("ORIG", "AFTER"))

    # Create a do_replace that behaves differently by path
    def do_replace_var(full_path, content, hunk):
        # full_path begins with "/abs/" by our fake abs_root_path
        if full_path.endswith("p1.txt"):
            # Simulate non-unique search
            raise FakeSearchTextNotUnique()
        if full_path.endswith("p2.txt"):
            # Simulate no match (empty content returned)
            return ""
        # p3 and others succeed
        return "OK"

    monkeypatch.setattr(udiff, "do_replace", do_replace_var)

    # Short error messages so that len(errors) < len(uniq) will be True when uniq has 3
    monkeypatch.setattr(udiff, "not_unique_error", "E1:{path}:{original}:{num_lines}")
    monkeypatch.setattr(udiff, "no_match_error", "E2:{path}:{original}:{num_lines}")
    monkeypatch.setattr(udiff, "other_hunks_applied", "<OTHER_HUNKS>")
    monkeypatch.setattr(udiff, "SearchTextNotUnique", FakeSearchTextNotUnique)

    write_calls = []
    self = make_self(write_calls)

    edits = [
        ("p1.txt", ["a\n"]),  # will raise SearchTextNotUnique
        ("p2.txt", ["b\n"]),  # will return empty -> no_match_error
        ("p3.txt", ["c\n"])   # will succeed and be written
    ]

    with pytest.raises(ValueError) as excinfo:
        udiff.UnifiedDiffCoder.apply_edits(self, edits)

    msg = str(excinfo.value)
    # The final message must include our 'other_hunks_applied' text because
    # we expect len(errors) < len(uniq) to be True here
    assert "<OTHER_HUNKS>" in msg
    # Ensure the individual error templates were used
    assert "E1:p1.txt" in msg
    assert "E2:p2.txt" in msg
    # p3 succeeded and was written once
    assert ("/abs/p3.txt", "OK") in write_calls


def test_errors_no_append_round_034(monkeypatch):
    """
    Two hunks both produce long error messages; the combined length of the
    joined errors will be larger than len(uniq), so the branch that appends
    other_hunks_applied should NOT run. We assert that the raised ValueError
    does not include the 'other_hunks_applied' text (lines 114-118).
    """
    monkeypatch.setattr(udiff, "normalize_hunk", lambda h: h)

    # Make original produced by hunk_to_before_after very long so formatted error strings are long
    monkeypatch.setattr(udiff, "hunk_to_before_after", lambda h: ("O" * 200, "AFTER"))

    def do_replace_raise(full_path, content, hunk):
        raise FakeSearchTextNotUnique()

    monkeypatch.setattr(udiff, "do_replace", do_replace_raise)

    # Template will include the long original, yielding a long error string
    monkeypatch.setattr(udiff, "not_unique_error", "LONGERR:{path}:{original}:{num_lines}")
    monkeypatch.setattr(udiff, "no_match_error", "NOMATCHERR:{path}:{original}:{num_lines}")
    monkeypatch.setattr(udiff, "other_hunks_applied", "<OTHER_HUNKS_SHOULD_NOT_BE_HERE>")
    monkeypatch.setattr(udiff, "SearchTextNotUnique", FakeSearchTextNotUnique)

    write_calls = []
    self = make_self(write_calls)

    # Two different hunks -> uniq length will be 2, but error strings are very long
    edits = [("x1.txt", ["z\n"]), ("x2.txt", ["y\n"])]

    with pytest.raises(ValueError) as excinfo:
        udiff.UnifiedDiffCoder.apply_edits(self, edits)

    msg = str(excinfo.value)
    # Because error messages are long, we do NOT expect other_hunks_applied to be appended
    assert "<OTHER_HUNKS_SHOULD_NOT_BE_HERE>" not in msg
    # The message should include the LONGERR marker for both hunks
    assert msg.count("LONGERR:") == 2
