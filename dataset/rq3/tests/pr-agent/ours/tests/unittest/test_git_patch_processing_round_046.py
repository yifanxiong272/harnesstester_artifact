import re
from types import SimpleNamespace
import pr_agent.algo.git_patch_processing as gpp


def _fake_settings(allow_dynamic_context, max_extra):
    return SimpleNamespace(config=SimpleNamespace(
        allow_dynamic_context=allow_dynamic_context,
        max_extra_lines_before_dynamic_context=max_extra,
    ))


def test_dynamic_context_found_header_round_046(monkeypatch):
    """When dynamic context is allowed and a matching section header is found
    in the extra 'before' lines, the returned hunk header should have the
    section header cleared (empty) in the constructed header line.
    This exercises the branch where lines_before_original_dynamic_context == lines_before_new_dynamic_context
    and sets found_header True (lines ~109-118).
    """
    # Patch settings to allow dynamic context and set dynamic window
    monkeypatch.setattr(gpp, "get_settings", lambda: _fake_settings(True, 2))
    # Ensure the RE matches our hunk header line
    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", re.compile(r"^@@"))
    # Force hunk header extraction to yield a section header and starts/sizes
    # section_header, size1, size2, start1, start2
    monkeypatch.setattr(gpp, "extract_hunk_headers", lambda match: ("SECTION_MARKER", 1, 1, 2, 2))
    # Pretend the hunk matches the original file
    monkeypatch.setattr(gpp, "check_if_hunk_lines_matches_to_file", lambda i, original, patch_lines, start1: True)

    # original and new file both contain the same line (with the section header)
    original_file = "SECTION_MARKER line before hunk\nline-in-hunk"
    new_file = "SECTION_MARKER line before hunk\nline-in-hunk"
    # Patch contains a single hunk header (matching RE_HUNK_HEADER)
    patch = "@@ -2,1 +2,1 @@ SECTION_MARKER\n+added-line"

    result = gpp.process_patch_lines(patch, original_file, patch_extra_lines_before=1, patch_extra_lines_after=0, new_file_str=new_file)

    # Find the produced hunk header line
    header_lines = [l for l in result.splitlines() if l.startswith('@@ -')]
    assert len(header_lines) == 1
    # Because section_header was cleared when dynamic context matched, header should end with '@@ ' (trailing space, empty section)
    assert header_lines[0].endswith(' @@ '), "Expected cleared section header (empty) in produced hunk header"


def test_dynamic_context_mini_match_round_046(monkeypatch):
    """When extra lines before the hunk differ between original and new files but
    they share a suffix, the implementation should find the mini-match and
    trim the delta lines accordingly. This exercises the found_mini_match loop
    (lines ~136-146).
    """
    # allow dynamic context (so the _calc_context_limits path executed), but this test's
    # important behavior happens later with delta_lines_original vs delta_lines_new
    monkeypatch.setattr(gpp, "get_settings", lambda: _fake_settings(True, 3))
    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", re.compile(r"^@@"))

    # Make the hunk start such that there are multiple lines before it
    # Return start1 = 4 so slices will include three lines before the hunk
    monkeypatch.setattr(gpp, "extract_hunk_headers", lambda match: ("SECTION_X", 1, 1, 4, 4))
    monkeypatch.setattr(gpp, "check_if_hunk_lines_matches_to_file", lambda i, original, patch_lines, start1: True)

    # original has ['A','B','C', 'hunkline'] ; new has ['X','B','C', 'hunkline']
    original_file = "A\nB\nC\nhunkline"
    new_file = "X\nB\nC\nhunkline"
    # header present
    patch = "@@ -4,1 +4,1 @@ SECTION_X\n+added-line"

    result = gpp.process_patch_lines(patch, original_file, patch_extra_lines_before=2, patch_extra_lines_after=0, new_file_str=new_file)

    # The mini-match should trim off the unmatched prefix 'A' so result should NOT contain ' A' but should contain the suffix lines ' B' and ' C'
    assert ' A' not in result
    assert ' B' in result and ' C' in result


def test_section_header_removal_without_dynamic_round_046(monkeypatch):
    """If dynamic context is disabled, but the extra original lines before the
    hunk contain the section header string, the code should remove the
    section header (lines ~158-162).
    """
    # Disable dynamic context
    monkeypatch.setattr(gpp, "get_settings", lambda: _fake_settings(False, 0))
    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", re.compile(r"^@@"))
    # Use a small hunk start so delta_lines_original will include our special line
    monkeypatch.setattr(gpp, "extract_hunk_headers", lambda match: ("MAGIC_SEC", 1, 1, 2, 2))
    monkeypatch.setattr(gpp, "check_if_hunk_lines_matches_to_file", lambda i, original, patch_lines, start1: True)

    # Put the section header text into the extra original line before the hunk
    original_file = "line containing MAGIC_SEC\nline-in-hunk"
    new_file = ""  # new file missing - dynamic context disabled path does not need new file
    patch = "@@ -2,1 +2,1 @@ MAGIC_SEC\n+added-line"

    result = gpp.process_patch_lines(patch, original_file, patch_extra_lines_before=1, patch_extra_lines_after=0, new_file_str=new_file)

    # The section header should have been cleared in the produced header line
    header_lines = [l for l in result.splitlines() if l.startswith('@@ -')]
    assert len(header_lines) == 1
    assert header_lines[0].endswith(' @@ '), "Expected cleared section header (empty) in produced hunk header when dynamic context disabled"
