def test_probe_001():
    # Import only the declared public entrypoint
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Activation: two hunks, first deletion-only, second contains an addition.
    patch_lines = [
        '@@ -1,1 +1,0 @@\n',
        '-deleted\n',
        '@@ -2,0 +2,1 @@\n',
        '+added\n',
    ]

    # Call the focused target unit
    result = omit_deletion_hunks(patch_lines)

    # Primary behavioral oracle: header immediately followed by the added line (no extra blank line), preserving trailing newlines
    expected = '@@ -2,0 +2,1 @@\n+added\n'

    assert result == expected, f"omit_deletion_hunks produced unexpected output: {result!r} (expected: {expected!r})"
