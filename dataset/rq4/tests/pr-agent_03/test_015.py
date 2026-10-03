from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    # deletion-only hunk (header + deletion line), both lines include trailing newlines
    del_header = "@@ -1,1 +1,0 @@\n"
    del_line = "-removed line 1\n"

    # addition-only hunk immediately follows (header + addition line), both lines include trailing newlines
    add_header = "@@ -2,0 +3,1 @@\n"
    add_line = "+added line 1\n"

    patch_lines = [del_header, del_line, add_header, add_line]

    result = omit_deletion_hunks(patch_lines)

    # Build list of non-empty lines for robust comparison against headers (strip blank lines introduced by joins)
    non_empty_lines = [ln for ln in result.split("\n") if ln.strip() != ""]

    # Primary oracle (single assert):
    # - output is non-empty
    # - first non-empty line is the addition hunk header (without trailing newline)
    # - no line in the result begins with '-' (no deletion lines leaked)
    assert non_empty_lines and non_empty_lines[0] == add_header.strip() and all(not ln.startswith("-") for ln in non_empty_lines), (
        "omit_deletion_hunks should start at the first added hunk header and contain no deletion lines; got: %r" % (result,)
    )
