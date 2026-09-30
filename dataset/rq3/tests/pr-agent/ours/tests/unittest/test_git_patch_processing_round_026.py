import types
from types import SimpleNamespace
from pr_agent.algo import git_patch_processing as gpp


def test_extract_hunk_left_round_026(monkeypatch):
    """Left-side selection: header matches hunk, deleted lines do not increment selected counter,
    'no newline at end of file' lines are skipped, and trailing chars are removed by default."""
    # Make RE_HUNK_HEADER.match deterministic: it will return the header string itself
    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", SimpleNamespace(match=lambda s: s))

    # Provide a deterministic extract_hunk_headers that returns values for start1/start2/size1/size2
    # For this test: start1=10, size1=5, start2=20, size2=5
    def fake_extract_hunk_headers(match):
        return ("@@", 5, 5, 10, 20)

    monkeypatch.setattr(gpp, "extract_hunk_headers", fake_extract_hunk_headers)

    # Prevent real logging side-effects
    monkeypatch.setattr(gpp, "get_logger", lambda: SimpleNamespace(error=lambda *a, **k: None))

    # Build a patch with one hunk. Include deletions and a 'no newline...' line to be skipped.
    patch_lines = [
        "@@ HUNK @@",
        " a",        # non-deletion -> corresponds to file line 10
        " b",        # non-deletion -> corresponds to file line 11 (should be selected)
        "-deleted",  # deletion -> should be present in patch_with_lines_str but not increment selected counter
        " d",        # non-deletion -> corresponds to file line 12 (should be selected)
        "No newline at end of file"  # should be skipped entirely
    ]
    patch = "\n".join(patch_lines)

    # We want to select lines 11-12 on the left side
    patch_with_lines_str, selected_lines = gpp.extract_hunk_lines_from_patch(
        patch, file_name=" testfile.py ", line_start=11, line_end=12, side="left", remove_trailing_chars=True
    )

    # Patch header should include the cleaned filename (strip()) and the hunk header
    assert "## File: 'testfile.py'" in patch_with_lines_str
    assert "@@ HUNK @@" in patch_with_lines_str

    # The 'no newline at end of file' line must not appear in the returned patch string
    assert "no newline at end of file" not in patch_with_lines_str.lower()

    # Selected lines should include only the non-deleted file lines that fall in the requested range
    # Using rstrip in the implementation removes the trailing newline; expect exact content
    assert selected_lines == " b\n d"


def test_extract_hunk_right_skip_then_select_round_026(monkeypatch):
    """Right-side selection across multiple hunks: first hunk skipped because line_start
    not in its right-side range; second hunk processed and only the matching right-side
    lines are collected. Ensure 'no newline...' skipped and when remove_trailing_chars=False
    trailing newlines remain."""
    # Deterministic matcher returning the header string
    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", SimpleNamespace(match=lambda s: s))

    # Provide a deterministic extract_hunk_headers that distinguishes hunk headers by content
    def fake_extract_hunk_headers(match):
        header = match
        if "HUNK1" in header:
            # First hunk: right side start2=30, size2=2 -> does not include our target line_start=36
            return ("@@", 2, 2, 10, 30)
        else:
            # Second hunk: right side start2=35, size2=5 -> covers line_start=36
            return ("@@", 3, 5, 20, 35)

    monkeypatch.setattr(gpp, "extract_hunk_headers", fake_extract_hunk_headers)
    monkeypatch.setattr(gpp, "get_logger", lambda: SimpleNamespace(error=lambda *a, **k: None))

    # Build a patch with two hunks. Include a 'No newline...' line for skipping.
    patch_lines = [
        "@@ HUNK1 @@",
        " x1",
        " x2",
        "@@ HUNK2 @@",
        " r1",     # right non-deletion -> corresponds to start2+0 = 35 -> not selected (we want 36)
        " r2",     # right non-deletion -> start2+1 = 36 -> should be selected
        "-rdel",   # deletion -> present in patch but does not increment selected counter
        " r3",
        "No newline at end of file"
    ]
    patch = "\n".join(patch_lines)

    # For right side, request the single file line 36..36; do not strip trailing characters so we observe them
    patch_with_lines_str, selected_lines = gpp.extract_hunk_lines_from_patch(
        patch, file_name="another_file.py", line_start=36, line_end=36, side="right", remove_trailing_chars=False
    )

    # The first hunk's body must be skipped (its lines should not be present after the first header in selection logic)
    # But the second hunk header must appear in the patch_with_lines_str and its lines should be present
    assert "@@ HUNK2 @@" in patch_with_lines_str
    assert " r1\n" in patch_with_lines_str
    assert "-rdel\n" in patch_with_lines_str

    # The 'No newline...' line must be skipped
    assert "no newline at end of file" not in patch_with_lines_str.lower()

    # Because remove_trailing_chars=False the selected line should keep its trailing newline
    assert selected_lines == " r2\n"
