def test_probe_001_omit_deletion_hunk_not_merged():
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Two consecutive hunks with no intervening lines:
    #  - first hunk is deletion-only
    #  - second hunk contains an addition
    patch_lines = [
        "@@ -1,1 +0,0 @@\n",
        "-deleted line\n",
        "@@ -2,0 +2,1 @@\n",
        "+added line\n",
    ]

    # According to the invariant, the output should contain only the added hunk's header
    # followed by a blank line and the '+' (and any context) lines from that hunk.
    expected_output = "@@ -2,0 +2,1 @@\n\n+added line\n"

    actual = omit_deletion_hunks(patch_lines)

    # Primary behavioral assertion: exact string equality. This will detect merging of the
    # deletion-only hunk into the following added hunk (buggy behavior).
    assert actual == expected_output, (
        "omit_deletion_hunks merged or preserved deletion-only hunk lines unexpectedly.\n"
        f"Expected: {expected_output!r}\nActual:   {actual!r}"
    )
