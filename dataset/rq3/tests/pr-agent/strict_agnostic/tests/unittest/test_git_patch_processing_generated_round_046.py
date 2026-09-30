import pytest
from types import SimpleNamespace
from pr_agent.algo import git_patch_processing as gpp

# Tests aim to exercise dynamic-context matching, mini-match trimming of extra lines,
# and the exception-handling fallback that returns the original patch string.


def test_dynamic_context_found_match_round_046(monkeypatch):
    # make settings allow dynamic context and set the dynamic context window
    settings = SimpleNamespace(config=SimpleNamespace(
        allow_dynamic_context=True,
        max_extra_lines_before_dynamic_context=2,
    ))
    monkeypatch.setattr(gpp, "get_settings", lambda: settings)

    # Prepare input such that the section header appears in the extra 'before' lines
    # and those extra lines are identical in original and new files -> found_header True
    patch_str = "@@ -3,1 +3,1 @@ headerA\n-oldline\n+newline"
    original_file = "unrelated\nheaderA context\noldline\nrest"
    new_file = "unrelated\nheaderA context\nnewline\nrest"

    # Request some extra lines before and after
    out = gpp.process_patch_lines(patch_str, original_file, patch_extra_lines_before=1, patch_extra_lines_after=1, new_file_str=new_file)

    # Expectations / oracle:
    # - dynamic context should find the header and remove it from the hunk header
    # - the function must return a string containing an hunk header; the section header
    #   text should not appear in the hunk header line itself (it may still appear as a delta line)
    assert isinstance(out, str)
    assert out.count("@@ -") >= 1
    # Find the hunk header line (the line that starts with @@) and ensure it does not include the section header
    header_line = next((ln for ln in out.splitlines() if ln.startswith("@@")), "")
    assert header_line != ""
    assert "headerA" not in header_line


def test_extra_lines_mismatch_and_mini_match_round_046(monkeypatch):
    # Disable dynamic context so the non-dynamic branch runs and section header removal can be tested
    settings = SimpleNamespace(config=SimpleNamespace(
        allow_dynamic_context=False,
        max_extra_lines_before_dynamic_context=1,
    ))
    monkeypatch.setattr(gpp, "get_settings", lambda: settings)

    # Construct files such that extra lines before are different but share a suffix
    # allowing the mini-match logic to trim the differing prefix and keep the matching suffix.
    # The section header ("mid") also appears in the extra lines and should be removed from header
    patch_str = "@@ -4,1 +4,1 @@ mid\n-oldline\n+newline"
    original_file = "a\nprefixA\nmid\noldline\nrest"
    new_file = "a\nprefixB\nmid\nnewline\nrest"

    out = gpp.process_patch_lines(patch_str, original_file, patch_extra_lines_before=2, patch_extra_lines_after=0, new_file_str=new_file)

    # Oracle assertions:
    # - the preserved mini-match suffix line (with a leading space) should be present in the output
    # - the section header 'mid' should not appear in the hunk header line
    assert isinstance(out, str)
    assert " mid" in out  # the kept suffix line should appear prefixed by a space
    header_line = next((ln for ln in out.splitlines() if ln.startswith("@@")), "")
    assert header_line != ""
    assert "mid" not in header_line


def test_exception_returns_original_round_046(monkeypatch):
    # Force RE_HUNK_HEADER.match to raise to hit the except path that returns the original patch
    def raising_match(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(gpp, "RE_HUNK_HEADER", SimpleNamespace(match=raising_match))

    patch_str = "@@ -1,1 +1,1 @@ something\n-old\n+new"
    original_file = "old"

    out = gpp.process_patch_lines(patch_str, original_file, patch_extra_lines_before=1, patch_extra_lines_after=1, new_file_str="new")

    # Oracle: on exception, the function should return the original patch string unchanged
    assert out == patch_str
