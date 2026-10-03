from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    # Two consecutive hunks: first is deletion-only, second contains an addition.
    patch_lines = [
        '@@ -1,1 +1,0 @@\n',
        '-deleted line A\n',
        '@@ -2,0 +2,1 @@\n',
        '+added line B\n'
    ]

    result = omit_deletion_hunks(patch_lines)

    # Primary oracle: no deletion ('-') lines should appear in the output.
    leaked_deletions = [ln for ln in result.splitlines() if ln.startswith('-')]
    assert leaked_deletions == [], f"Deletion-only hunk lines leaked into output: {leaked_deletions}\nfull output: {result!r}"

    # Supporting observable checks: the added hunk header and its '+' line must be preserved.
    assert '@@ -2,0 +2,1 @@' in result, "Added hunk header missing from output"
    assert '+added line B' in result, "Added line from the second hunk missing from output"
