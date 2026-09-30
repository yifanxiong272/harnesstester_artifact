# file: aider/coders/udiff_coder.py:69-118
# asked: {"lines": [73, 74, 75, 77, 78, 80, 81, 82, 84, 88, 89, 91, 93, 94, 95, 96, 97, 98, 101, 103, 104, 105, 106, 109, 112, 115, 116, 117, 118], "branches": [[72, 73], [74, 75], [74, 77], [80, 81], [80, 82], [87, 88], [103, 104], [103, 112], [114, 115], [116, 117], [116, 118]]}
# gained: {"lines": [73, 74, 75, 77, 78, 80, 81, 82, 84, 88, 89, 91, 93, 94, 95, 96, 97, 98, 101, 103, 104, 105, 106, 109, 112, 115, 116, 117, 118], "branches": [[72, 73], [74, 75], [74, 77], [80, 81], [80, 82], [87, 88], [103, 104], [103, 112], [114, 115], [116, 117], [116, 118]]}

import importlib
import pytest
from types import SimpleNamespace

from aider.coders.search_replace import SearchTextNotUnique


def make_coder_and_patch(monkeypatch):
    """
    Import the udiff_coder module, create a UnifiedDiffCoder instance without running
    its __init__ (to avoid heavy dependencies), and prepare common monkeypatch targets.
    Returns (module, coder, writes) where writes is a dict recording writes.
    """
    m = importlib.import_module("aider.coders.udiff_coder")
    CoderClass = getattr(m, "UnifiedDiffCoder")

    # Create instance without calling __init__
    coder = object.__new__(CoderClass)

    # Capture writes
    writes = {}

    class IO:
        pretty = False
        encoding = "utf-8"
        chat_history_file = "/dev/null"

        def read_text(self, full_path):
            # Return a placeholder content; do_replace will decide behavior.
            return f"ORIG_CONTENT_OF:{full_path}"

        def write_text(self, full_path, content):
            writes[full_path] = content

        # provide placeholders for methods that might be called elsewhere (not used here)
        def tool_warning(self, *args, **kwargs):
            pass

        def tool_output(self, *args, **kwargs):
            pass

    coder.io = IO()

    # Make abs_root_path deterministic
    coder.abs_root_path = lambda path: f"/abs/{path}"

    return m, coder, writes


def test_apply_edits_appends_other_hunks_when_errors_short(monkeypatch):
    """
    Test the branch where errors exist and the joined error string length is shorter than
    the number of unique hunks, so other_hunks_applied is appended and ValueError is raised.
    Also exercises normalize_hunk skipping and duplicate skipping, and the successful write_text path.
    """
    m, coder, writes = make_coder_and_patch(monkeypatch)

    # Prepare many unique hunks so len(uniq) is large.
    uniq_count = 10
    edits = []
    # Add one hunk that will produce an empty replacement (no match) -> error
    edits.append(("p_err", ["ERR\n"]))
    # Add many hunks that will apply successfully
    for i in range(uniq_count - 1):
        edits.append((f"p_ok_{i}", [f"OK{i}\n"]))
    # Add a duplicate that should be skipped by seen logic (duplicate of p_ok_0)
    edits.append(("p_ok_0", ["OK0\n"]))
    # Add a hunk that normalize_hunk will turn into empty (skipped)
    edits.append(("skip_me", ["__EMPTY__"]))

    # Patch normalize_hunk to return empty list for the special marker, else identity
    def normalize_hunk(hunk):
        if hunk == ["__EMPTY__"]:
            return []
        return hunk

    # hunk_to_before_after: return a tiny original so the joined error string is short
    def hunk_to_before_after(hunk):
        return ("X", "Y")

    # do_replace: return empty for p_err to trigger no_match error; non-empty for others
    def do_replace(full_path, content, hunk):
        if full_path.endswith("/p_err"):
            return ""  # triggers no match error
        return f"NEW_CONTENT_FOR:{full_path}"

    # Set short error templates and other_hunks_applied
    monkeypatch.setattr(m, "normalize_hunk", normalize_hunk)
    monkeypatch.setattr(m, "hunk_to_before_after", hunk_to_before_after)
    monkeypatch.setattr(m, "do_replace", do_replace)
    monkeypatch.setattr(m, "no_match_error", "E")  # very short
    monkeypatch.setattr(m, "not_unique_error", "N")
    monkeypatch.setattr(m, "other_hunks_applied", "--OTHER-HUNKS--")

    # Now call apply_edits and assert it raises ValueError with other_hunks_applied appended
    with pytest.raises(ValueError) as exc:
        coder.apply_edits(edits)

    msg = str(exc.value)
    assert "--OTHER-HUNKS--" in msg
    # Also assert that writes happened for the successful hunks (uniq_count - 1 of them)
    # Note: duplicate p_ok_0 should not create an extra write.
    expected_writes = uniq_count - 1  # all except p_err
    assert len(writes) == expected_writes
    # Check one of the writes content is what do_replace returned
    assert writes["/abs/p_ok_1"] == "NEW_CONTENT_FOR:/abs/p_ok_1"


def test_apply_edits_not_unique_and_no_suffix_when_long_errors(monkeypatch):
    """
    Test the branch where errors exist but the joined error string length is
    greater-or-equal to the number of unique hunks, so other_hunks_applied is NOT appended.
    Also exercises the SearchTextNotUnique exception handling and write_text for successes.
    """
    m, coder, writes = make_coder_and_patch(monkeypatch)

    # Build edits: two unique hunks both will generate errors (one raises SearchTextNotUnique,
    # the other returns empty), so len(uniq) is small and errors string will be long.
    edits = [
        ("p_nu", ["NU\n"]),   # will raise SearchTextNotUnique
        ("p_nm", ["NM\n"]),   # will return empty (no match)
        # include a duplicate to ensure duplicate branch executed
        ("p_nu", ["NU\n"]),
        # include a skip to exercise normalize_hunk->empty skip
        ("skip_marker", ["__EMPTY__"]),
    ]

    def normalize_hunk(hunk):
        if hunk == ["__EMPTY__"]:
            return []
        return hunk

    # Provide long original so error messages become long
    def hunk_to_before_after(hunk):
        # Make original length fairly long to ensure len(errors) >= len(uniq)
        return ("ORIGINAL_LONG_" + ("x" * 50), "")

    # do_replace: p_nu raises SearchTextNotUnique, p_nm returns empty
    def do_replace(full_path, content, hunk):
        if full_path.endswith("/p_nu"):
            raise SearchTextNotUnique("ambiguous")
        if full_path.endswith("/p_nm"):
            return ""
        return "SHOULD_NOT_HAPPEN"

    # Long error templates so that joined error string length >= uniq count (uniq is small)
    long_template = "ERROR_LONG_" + ("y" * 100)
    monkeypatch.setattr(m, "normalize_hunk", normalize_hunk)
    monkeypatch.setattr(m, "hunk_to_before_after", hunk_to_before_after)
    monkeypatch.setattr(m, "do_replace", do_replace)
    monkeypatch.setattr(m, "no_match_error", long_template)
    monkeypatch.setattr(m, "not_unique_error", long_template)
    monkeypatch.setattr(m, "other_hunks_applied", "--OTHER-HUNKS--")

    with pytest.raises(ValueError) as exc:
        coder.apply_edits(edits)

    msg = str(exc.value)
    # Because error messages are long, the shortness check should fail and the suffix should NOT be present
    assert "--OTHER-HUNKS--" not in msg
    # Both error kinds should be present (not-unique and no-match) as substrings of combined message
    assert "ERROR_LONG_" in msg
