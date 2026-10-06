def test_probe_001():
    # Import only the declared public entrypoint for the focused unit
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Construct activation-condition input: two consecutive hunks
    patch_lines = [
        # First hunk: deletion-only (no '+' lines)
        "@@ -1,1 +1,0 @@\n",
        "-deleted line hunk1\n",
        # Second hunk: contains an addition
        "@@ -2,0 +2,1 @@\n",
        "+added line hunk2\n",
    ]

    result = omit_deletion_hunks(patch_lines)

    # Primary behavioral oracle (one assertion group forming the single observable check):
    # - second hunk header and its '+' line must be present
    # - first hunk '-' line must NOT be present
    assert "@@ -2,0 +2,1 @@" in result, "expected second hunk header to appear in output"
    assert "+added line hunk2" in result, "expected added line from second hunk to appear in output"
    assert "-deleted line hunk1" not in result, "deletion-only hunk from the first hunk must be omitted"
