# file: pr_agent/algo/git_patch_processing.py:414-464
# asked: {"lines": [415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 427, 428, 429, 430, 432, 434, 437, 439, 440, 441, 442, 443, 444, 445, 446, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 460, 461, 462, 464], "branches": [[423, 424], [423, 460], [424, 425], [424, 427], [427, 428], [427, 448], [437, 439], [437, 442], [439, 440], [439, 446], [442, 443], [442, 446], [443, 444], [443, 446], [448, 423], [448, 449], [449, 450], [449, 451], [451, 452], [451, 453], [454, 423], [454, 455], [460, 461], [460, 464]]}
# gained: {"lines": [415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 427, 428, 429, 430, 432, 434, 437, 439, 440, 441, 442, 443, 446, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 460, 461, 462, 464], "branches": [[423, 424], [423, 460], [424, 427], [427, 428], [427, 448], [437, 439], [437, 442], [439, 440], [439, 446], [442, 443], [443, 446], [448, 423], [448, 449], [449, 450], [449, 451], [451, 452], [451, 453], [454, 423], [454, 455], [460, 461]]}

import types
import pytest

from pr_agent.algo import git_patch_processing as gpp


def test_extract_hunk_lines_from_patch_right_side_selection():
    patch = (
        "@@ -1,3 +10,5 @@\n"
        " line1\n"
        "+line2\n"
        "-line3\n"
        " line4\n"
        "+line5\n"
    )
    file_name = "test.txt"
    # start2 from header is 10, we want to capture lines mapped to 12..13
    line_start = 12
    line_end = 13
    patch_with_lines_str, selected_lines = gpp.extract_hunk_lines_from_patch(
        patch, file_name, line_start, line_end, side="right", remove_trailing_chars=True
    )

    # patch_with_lines_str should contain the file header and the hunk header and all lines (without trailing newline)
    assert f"## File: '{file_name}'" in patch_with_lines_str
    assert "@@ -1,3 +10,5 @@" in patch_with_lines_str
    assert "line1" in patch_with_lines_str and "line5" in patch_with_lines_str

    # Expected selected lines computed according to the function logic
    expected_selected = "-line3\n line4\n+line5"
    assert selected_lines == expected_selected


def test_extract_hunk_lines_from_patch_left_side_with_skip_and_select():
    # Two hunks: first does not include the requested left-side line_start so it should be skipped.
    # Second hunk includes the left-side line_start and its lines should be selected appropriately.
    patch = (
        "@@ -1,2 +1,2 @@\n"
        " a\n"
        " b\n"
        "@@ -5,4 +10,4 @@\n"
        " c\n"
        " d\n"
    )
    file_name = "file2.txt"
    # For the second hunk start1 = 5, selected_lines_num starts at 0 so first line maps to 5, second to 6.
    line_start = 6
    line_end = 6
    patch_with_lines_str, selected_lines = gpp.extract_hunk_lines_from_patch(
        patch, file_name, line_start, line_end, side="left", remove_trailing_chars=True
    )

    # First hunk header should not be present because it was skipped; second should be present.
    assert "@@ -1,2 +1,2 @@" not in patch_with_lines_str
    assert "@@ -5,4 +10,4 @@" in patch_with_lines_str

    # According to the function logic both lines in the second hunk are selected for the given range
    assert selected_lines == " c\n d"


def test_extract_hunk_lines_from_patch_exception_branch(monkeypatch):
    # Force an exception during RE_HUNK_HEADER.match to exercise the except branch and logging.
    original_re = gpp.RE_HUNK_HEADER
    # Create a fake RE_HUNK_HEADER with a match method that raises
    fake_re = types.SimpleNamespace(match=lambda s: (_ for _ in ()).throw(RuntimeError("forced match failure")))
    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", fake_re)

    # Replace get_logger to capture error call
    class FakeLogger:
        def __init__(self):
            self.errors = []

        def error(self, msg, artifact=None):
            self.errors.append((msg, artifact))

    fake_logger = FakeLogger()
    monkeypatch.setattr(gpp, "get_logger", lambda: fake_logger)

    patch = "@@ -1,1 +1,1 @@\n line\n"
    res = gpp.extract_hunk_lines_from_patch(patch, "f", 1, 1, side="left", remove_trailing_chars=True)
    # Should return empty strings on exception
    assert res == ("", "")
    # Ensure logger.error was called
    assert len(fake_logger.errors) == 1
    msg, artifact = fake_logger.errors[0]
    assert "Failed to extract hunk lines from patch" in msg
    assert isinstance(artifact, dict) and "traceback" in artifact

    # monkeypatch will restore RE_HUNK_HEADER and get_logger after test automatically
