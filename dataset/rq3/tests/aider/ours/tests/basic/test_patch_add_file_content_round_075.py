import pytest

from aider.coders.patch_coder import (
    PatchCoder,
    PatchAction,
    ActionType,
    DiffError,
)


def test_parse_add_file_content_add_lines_and_sentinel_round_075():
    # Lines that include two added lines and then a sentinel should stop before the sentinel
    lines = [
        "+first line",
        "+second line",
        "*** Update File: some/path.py",
    ]

    # Call the unbound method; the method does not use self attributes for this logic
    action, next_index = PatchCoder._parse_add_file_content(object(), lines, 0)

    # Expect the action to be an ADD with joined content (no leading '+') and index at sentinel
    assert isinstance(action, PatchAction)
    assert action.type == ActionType.ADD
    assert action.path == ""
    assert action.new_content == "first line\nsecond line"
    assert next_index == 2


def test_parse_add_file_content_with_blank_line_round_075():
    # Blank/whitespace-only lines within add content are treated as blank added lines
    lines = [
        "+a",
        "   ",  # whitespace-only line should become an empty added line
        "+b",
        "*** End Patch",
    ]

    action, next_index = PatchCoder._parse_add_file_content(object(), lines, 0)

    # The middle blank line should produce an empty line in the joined content
    assert action.new_content == "a\n\nb"
    assert action.type == ActionType.ADD
    # Ensure we stopped at the sentinel (index points to the sentinel line)
    assert next_index == 3


def test_parse_add_file_content_invalid_line_raises_round_075():
    # A non-'+' non-blank line should raise DiffError with the offending line in the message
    lines = [
        "+ok",
        "this line is missing plus",
        "+after",
    ]

    with pytest.raises(DiffError) as excinfo:
        PatchCoder._parse_add_file_content(object(), lines, 0)

    # Verify the error message includes the invalid line text
    assert "Invalid Add File line (missing '+'): this line is missing plus" in str(excinfo.value)
