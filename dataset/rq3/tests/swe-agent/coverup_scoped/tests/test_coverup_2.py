# file: sweagent/agent/history_processors.py:179-222
# asked: {"lines": [195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 214, 215, 216, 217, 218, 220, 221, 222], "branches": [[197, 198], [197, 222], [199, 200], [199, 202], [202, 203], [202, 205], [206, 207], [206, 221], [208, 209], [208, 211], [212, 213], [212, 220]]}
# gained: {"lines": [195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 214, 215, 216, 217, 218, 220, 221, 222], "branches": [[197, 198], [197, 222], [199, 200], [199, 202], [202, 203], [202, 205], [206, 207], [206, 221], [208, 209], [208, 211], [212, 213], [212, 220]]}

import pytest

from sweagent.agent.history_processors import ClosedWindowHistoryProcessor


def make_entry(role="user", content="", is_demo=False):
    entry = {"role": role, "content": content}
    if is_demo:
        entry["is_demo"] = True
    return entry


def test_closed_window_processor_replaces_old_windows_and_preserves_others():
    proc = ClosedWindowHistoryProcessor()

    # Old entry for foo.py (should be replaced because a newer window exists later)
    old_content = (
        "1: old line one\n"
        "2: old line two\n"
        "[File: foo.py (2 lines total)]\n"
        "Some trailing text\n"
    )
    old_entry = make_entry(role="user", content=old_content)

    # A user entry with no numbered lines (matches == 0) should be kept unchanged
    no_match_content = "Just some plain text without numbered lines."
    no_match_entry = make_entry(role="user", content=no_match_content)

    # A newer entry for foo.py (this is the last window and should be preserved)
    new_content = (
        "1: new line only\n"
        "[File: foo.py (1 lines total)]\n"
    )
    new_entry = make_entry(role="user", content=new_content)

    # A non-user entry should be appended unchanged
    assistant_content = "Assistant message that should remain untouched."
    assistant_entry = make_entry(role="assistant", content=assistant_content)

    # A demo user entry should be appended unchanged (is_demo True)
    demo_content = "Demo user content should not be processed."
    demo_entry = make_entry(role="user", content=demo_content)
    demo_entry["is_demo"] = True

    # An entry with numbered lines but missing the file annotation -> should be skipped (continue)
    no_file_annotation_content = "1: stray numbered line\n2: another line\nNo file info here."
    no_file_annotation_entry = make_entry(role="user", content=no_file_annotation_content)

    # Compose history. Order matters: the 'new_entry' must appear after 'old_entry' so
    # that when processing reversed(history) the processor will see the new window first
    # and then mark the earlier (old_entry) as outdated.
    history = [
        old_entry,
        no_match_entry,
        new_entry,
        assistant_entry,
        demo_entry,
        no_file_annotation_entry,
    ]

    # Keep a deep copy of originals to assert original entries are not mutated
    import copy
    original_history_copy = copy.deepcopy(history)

    result = proc(history)

    # no_file_annotation_entry should be skipped (not present)
    assert all(
        e["content"] != no_file_annotation_content for e in result
    ), "Entries without file annotation but with numbered lines should be skipped."

    # Length should be original minus the skipped one
    assert len(result) == len(history) - 1

    # The order of returned entries should match the original order (except skipped)
    expected_order_contents = [
        old_content,            # replaced in result (but original unchanged)
        no_match_content,       # unchanged
        new_content,            # unchanged (latest window)
        assistant_content,      # unchanged
        demo_content,           # unchanged (is_demo True)
    ]
    assert [e["content"] for e in result] == [
        # But old_content will be replaced in the result; so replace expected first item accordingly below
        # We'll check the replaced item's content separately, so just compare remaining ones here.
        result[0]["content"],
        no_match_content,
        new_content,
        assistant_content,
        demo_content,
    ]

    # Verify original history entries were not mutated (important: processor uses entry.copy())
    assert history == original_history_copy

    # Check that the first returned entry (corresponding to old_entry) was replaced with the proper summary
    replaced_entry = result[0]
    assert "Outdated window with 2 lines omitted..." in replaced_entry["content"]
    # Ensure the replacement used the correct number of matched lines (2)
    assert "2 lines omitted" in replaced_entry["content"]

    # Ensure the new_entry remained unchanged
    # Find the item matching new_entry by role and content
    found_new = [e for e in result if e["content"] == new_content and e["role"] == "user"]
    assert len(found_new) == 1

    # Ensure assistant and demo entries are present and unchanged
    assert any(e["role"] == "assistant" and e["content"] == assistant_content for e in result)
    assert any(e.get("is_demo", False) and e["content"] == demo_content for e in result)


def test_closed_window_processor_handles_no_matches_and_no_file_match_branch():
    proc = ClosedWindowHistoryProcessor()

    # User entry with no numbered lines (len(matches) == 0) -> should be appended unchanged
    simple_entry = make_entry(role="user", content="Nothing to match here.")

    # User entry with numbered lines but missing file annotation -> should be skipped
    numbered_no_file = make_entry(role="user", content="1: line one\n2: line two\nNo [File: ...] here.")

    history = [simple_entry, numbered_no_file]

    result = proc(history)

    # simple_entry should be present
    assert any(e["content"] == simple_entry["content"] for e in result)

    # numbered_no_file should be skipped
    assert all("line one" not in e["content"] for e in result)
