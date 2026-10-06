def test_probe_001():
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Deletion-only hunk immediately followed by an addition-only hunk (no separating context lines)
    patch_lines = [
        "@@ -1,2 +1,0 @@\n",
        "-deleted line 1\n",
        "-deleted line 2\n",
        "@@ -3,0 +3,2 @@\n",
        "+added line 1\n",
        "+added line 2\n",
    ]

    result = omit_deletion_hunks(patch_lines)
    result_lines = result.splitlines()

    # Primary behavioral invariant: no input deletion lines (lines that start with '-') appear in the output
    assert not any(l.startswith('-') for l in result_lines), (
        "omit_deletion_hunks leaked deletion lines into the output: %r" % result_lines
    )

    # Supporting assertions: addition hunk header and added lines are preserved in the output
    assert "@@ -3,0 +3,2 @@" in result, "expected addition hunk header missing from result"
    assert any(l.startswith('+added line 1') for l in result_lines), "expected '+added line 1' missing"
    assert any(l.startswith('+added line 2') for l in result_lines), "expected '+added line 2' missing"
