from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    # Deletion-only hunk immediately followed by an added hunk.
    deletion_hunk_header = "@@ -1,2 +1,0 @@\n"
    deletion_lines = ["-old line 1\n", "-old line 2\n"]

    added_hunk_header = "@@ -3,0 +3,2 @@\n"
    added_lines = ["+new1\n", "+new2\n"]

    # Assemble input: header then its '-' lines, then next header then its '+' lines.
    patch_lines = [deletion_hunk_header] + deletion_lines + [added_hunk_header] + added_lines

    result = omit_deletion_hunks(patch_lines)

    # Primary behavioral oracle (presence / absence):
    # The added hunk header and its '+' lines must appear.
    assert added_hunk_header.strip() in result, (
        "Expected added-hunk header to be present in result but it was missing.\nResult:\n" + repr(result)
    )
    assert "+new1" in result and "+new2" in result, (
        "Expected added '+' lines to be present in result but one or more were missing.\nResult:\n" + repr(result)
    )

    # The deletion-only hunk header and its '-' lines must not appear.
    assert deletion_hunk_header.strip() not in result, (
        "Deletion-only hunk header must not appear in result (leak detected).\nResult:\n" + repr(result)
    )
    assert "-old line 1" not in result and "-old line 2" not in result, (
        "Deletion lines from a deletion-only hunk must not appear in result (leak detected).\nResult:\n" + repr(result)
    )
