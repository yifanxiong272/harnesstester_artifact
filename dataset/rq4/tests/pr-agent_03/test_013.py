def test_probe_001():
    # Directly exercise the public entrypoint
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # First hunk: deletion-only (two '-' lines). Immediately followed by
    # second hunk: addition-only (two '+' lines). All lines are newline-terminated
    # to exercise line-based parsing deterministically.
    patch_lines = [
        "@@ -1,2 +1,0 @@\n",
        "-deleted line 1\n",
        "-deleted line 2\n",
        "@@ -3,0 +3,2 @@\n",
        "+added line A\n",
        "+added line B\n",
    ]

    result = omit_deletion_hunks(patch_lines)

    # Primary behavioral oracle: no deletion lines ('-') should appear in the output.
    assert not any(line.startswith("-") for line in result.splitlines()), (
        "omit_deletion_hunks must not include deletion lines in its returned patch string; got:\n" + result
    )
