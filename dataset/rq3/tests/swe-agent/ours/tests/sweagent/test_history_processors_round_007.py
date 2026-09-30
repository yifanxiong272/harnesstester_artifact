import pytest
from sweagent.agent.history_processors import ClosedWindowHistoryProcessor


def test_non_user_demo_and_no_pattern_round_007():
    """Non-user entries and demo user entries should be preserved; user entries with no numbered-line pattern
    should be preserved (no trimming or skipping).
    """
    processor = ClosedWindowHistoryProcessor()

    assistant_entry = {"role": "assistant", "content": "assistant reply"}
    demo_user_entry = {"role": "user", "content": "[File: demo.py (1 lines total)]\nno numbers here", "is_demo": True}
    user_no_match = {"role": "user", "content": "This user message has no numbered lines"}

    history = [assistant_entry, demo_user_entry, user_no_match]

    out = processor(history)

    # All items should be present and in the same order
    assert len(out) == 3
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == "assistant reply"

    # demo user entry should be preserved exactly (is_demo bypasses processing)
    assert out[1]["role"] == "user"
    assert out[1]["is_demo"] is True
    assert out[1]["content"] == demo_user_entry["content"]

    # user entry without numbered lines should be preserved (no trimming)
    assert out[2]["role"] == "user"
    assert out[2]["content"] == user_no_match["content"]


def test_skip_when_filepattern_missing_round_007():
    """When numbered-line matches exist but no [File: ...] pattern is found, the entry should be skipped (dropped).
    """
    processor = ClosedWindowHistoryProcessor()

    # An entry that has numbered lines but no file header -> should be dropped
    user_with_numbers_no_file = {
        "role": "user",
        "content": "1: one\n2: two\n3: three\nremaining text"
    }

    # Another regular user entry that will remain
    another_user = {"role": "user", "content": "Hello world"}

    history = [user_with_numbers_no_file, another_user]

    out = processor(history)

    # The entry with numbered lines but no file header should be omitted; only the second entry remains
    assert len(out) == 1
    assert out[0]["content"] == "Hello world"


def test_trim_outdated_windows_round_007():
    """When two user entries reference the same file, the older (earlier in history) entry should be trimmed
    to contain the "Outdated window" message and preserve content before the numbered block and after it.
    """
    processor = ClosedWindowHistoryProcessor()

    header = "[File: example.py (10 lines total)]\n"
    numbered_block = "1: first\n2: second\n3: third\n"
    tail = "TAIL_TEXT\n"

    # older entry (index 0) - should be trimmed after processing
    old_entry = {"role": "user", "content": header + numbered_block + tail}

    # newer entry (index 1) - appears later in history, so when iterating reversed it's seen first and will add file to windows
    new_entry = {"role": "user", "content": header + numbered_block + "NEW_END\n"}

    history = [old_entry, new_entry]

    out = processor(history)

    # Both entries should remain in order
    assert len(out) == 2

    # The newer entry should remain unchanged (it was the last shown window)
    assert out[1]["content"] == new_entry["content"]

    # The older entry should have been trimmed: header + omitted message + tail
    trimmed = out[0]["content"]

    assert trimmed.startswith(header)
    assert "Outdated window with 3 lines omitted...\n" in trimmed
    # The tail after numbered_block should be preserved
    assert trimmed.endswith(tail)

    # Ensure that the omitted message reports the correct count (3 numbered lines)
    assert "Outdated window with 3 lines omitted...\n" == trimmed[len(header): len(header) + len("Outdated window with 3 lines omitted...\n")]
