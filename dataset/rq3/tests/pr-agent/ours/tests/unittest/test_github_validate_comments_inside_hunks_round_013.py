import copy
import re
import difflib
import types

import pr_agent.git_providers.github_provider as gp
import pytest


class CapturingLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, *args, **kwargs):
        # join positional args for easier assertions
        self.infos.append(" ".join(str(a) for a in args))

    def error(self, *args, **kwargs):
        self.errors.append(" ".join(str(a) for a in args))


class DummyFile:
    def __init__(self, filename, patch):
        self.filename = filename
        self.patch = patch


class DummyProvider:
    def __init__(self, diff_files):
        self._diff_files = diff_files

    def get_diff_files(self):
        # return the same instances so tests can observe added attributes
        return self._diff_files


@pytest.fixture(autouse=True)
def patch_helpers(monkeypatch):
    """Patch external helpers resolved in the module under test to deterministic, test-safe implementations."""

    # set_file_languages should be identity for tests
    monkeypatch.setattr(gp, "set_file_languages", lambda files: files)

    # extract_hunk_headers: parse a match produced by RE_HUNK_HEADER and return values in the order expected
    def fake_extract_hunk_headers(match):
        # groups: (start1, size1?, start2, size2?, rest)
        g1, g2, g3, g4, rest = match.groups()
        size1 = int(g2) if g2 is not None else 1
        size2 = int(g4) if g4 is not None else 1
        start1 = int(g1)
        start2 = int(g3)
        section_header = rest
        return (section_header, size1, size2, start1, start2)

    monkeypatch.setattr(gp, "extract_hunk_headers", fake_extract_hunk_headers)

    # logger capturing
    logger = CapturingLogger()
    monkeypatch.setattr(gp, "get_logger", lambda: logger)

    return logger


def test_continue_when_missing_fields_round_013(patch_helpers):
    """If a suggestion lacks relevant_lines_start/end/original_suggestion it is skipped (unchanged in returned copy)."""
    # patch contains a simple hunk header; provider returns a file with that patch
    file = DummyFile("file.py", "@@ -1,1 +10,1 @@\n+line\n")
    provider = DummyProvider([file])

    suggestions = [
        {"relevant_file": "file.py", "body": "no original suggestion present"}
    ]

    # Call the method under test with a simple dummy 'self' (provider)
    out = gp.GithubProvider.validate_comments_inside_hunks(provider, suggestions)

    # returned should be a deepcopy (not the same objects) but equal in content
    assert out == suggestions
    assert out is not suggestions


def test_valid_hunk_preserves_lines_round_013(patch_helpers):
    """If the comment is fully inside a hunk, the suggestion remains committable and file.patches_range is created."""
    # Create a patch with a hunk that starts at +10 and has 3 lines (10..12)
    patch_text = "@@ -1,1 +10,3 @@ description\n+lineA\n+lineB\n+lineC\n"
    file = DummyFile("file.py", patch_text)
    provider = DummyProvider([file])

    suggestions = [
        {
            "relevant_file": "file.py",
            "relevant_lines_start": 11,
            "relevant_lines_end": 11,
            "original_suggestion": {"existing_code": "a\n", "improved_code": "b\n"},
            "body": "some code comment",
        }
    ]

    out = gp.GithubProvider.validate_comments_inside_hunks(provider, suggestions)

    # suggestion inside hunk should be preserved
    assert out[0]["relevant_lines_start"] == 11
    assert out[0]["relevant_lines_end"] == 11

    # file.patches_range should have been generated and cover lines 10..12
    assert hasattr(file, "patches_range")
    assert file.patches_range == [{"start": 10, "end": 12}]


def test_near_hunk_adjusts_and_injects_diff_round_013(patch_helpers):
    """When a comment is close to a hunk but not strictly inside, it is clipped and its body replaced with a diff detail."""
    # Hunk at +50 with size 3 -> covers 50..52
    patch_text = "@@ -1,1 +50,3 @@ descr\n+AAA\n+BBB\n+CCC\n"
    file = DummyFile("file.py", patch_text)
    provider = DummyProvider([file])

    # Put comment partially outside but close (start 55 end 56) -> distance 4
    suggestions = [
        {
            "relevant_file": "file.py",
            "relevant_lines_start": 55,
            "relevant_lines_end": 56,
            "original_suggestion": {"existing_code": "old_line1\nold_line2\n", "improved_code": "new_line1\nnew_line2\n"},
            "body": "Here is a suggestion:\n```suggestion\nold_line1\nold_line2\n```\n",
        }
    ]

    out = gp.GithubProvider.validate_comments_inside_hunks(provider, suggestions)

    # The function should clip the suggestion within the nearest patch_range bounds
    # After clipping, start should be max(original_start, patch_start)=55 and end=min(original_end, patch_end)=52
    # This may produce start > end but the code assigns the clipped values; assert they were changed
    assert out[0]["relevant_lines_start"] == max(55, 50)
    assert out[0]["relevant_lines_end"] == min(56, 52)

    # The body should have been replaced to include the 'New proposed code' details
    assert "<details><summary>New proposed code:" in out[0]["body"]
    assert out[0]["body"].strip().endswith("</details>")


def test_far_from_hunk_logs_error_round_013(patch_helpers):
    """If a comment is far from any hunk (distance >= 10), the function logs an error and does not change the suggestion."""
    logger = patch_helpers

    # Hunk at +1 size 1 -> covers 1..1
    patch_text = "@@ -1,1 +1,1 @@ descr\n+L1\n"
    file = DummyFile("file.py", patch_text)
    provider = DummyProvider([file])

    # Put comment far away (start 100, end 100) -> large distance
    suggestions = [
        {
            "relevant_file": "file.py",
            "relevant_lines_start": 100,
            "relevant_lines_end": 100,
            "original_suggestion": {"existing_code": "x\n", "improved_code": "y\n"},
            "body": "unchanged body",
        }
    ]

    out = gp.GithubProvider.validate_comments_inside_hunks(provider, suggestions)

    # Suggestion should remain unchanged because it is considered not inside any hunk and too far
    assert out[0]["relevant_lines_start"] == 100
    assert out[0]["relevant_lines_end"] == 100

    # Logger should have at least one error message mentioning it is not inside a valid hunk
    errors = logger.errors
    assert any("Comment is not inside a valid hunk" in e for e in errors)


def test_exception_logs_error_round_013(patch_helpers):
    """If an exception occurs while processing a file patch (e.g., patch is None), it is caught and logged."""
    logger = patch_helpers

    # Make a file whose patch is None to provoke an AttributeError on splitlines()
    file = DummyFile("file.py", None)
    provider = DummyProvider([file])

    suggestions = [
        {
            "relevant_file": "file.py",
            "relevant_lines_start": 1,
            "relevant_lines_end": 1,
            "original_suggestion": {"existing_code": "a\n", "improved_code": "b\n"},
            "body": "something",
        }
    ]

    out = gp.GithubProvider.validate_comments_inside_hunks(provider, suggestions)

    # The function should return a copy even if an exception occurred
    assert out == suggestions

    # Logger should have recorded a failure processing the patch
    assert any("Failed to process patch for committable comment" in e for e in logger.errors)
