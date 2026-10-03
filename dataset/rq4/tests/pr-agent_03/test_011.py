from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    # First hunk: deletion-only
    # Second hunk: addition-only
    patch_lines = [
        '@@ -1,1 +1,0 @@\n',
        '-deleted line\n',
        '@@ -2,0 +2,1 @@\n',
        '+added line\n',
    ]

    result = omit_deletion_hunks(patch_lines)

    # Expected: only the addition-only hunk preserved, header, a blank separator line, then the + lines
    expected = '@@ -2,0 +2,1 @@\n\n+added line\n'

    assert result == expected
