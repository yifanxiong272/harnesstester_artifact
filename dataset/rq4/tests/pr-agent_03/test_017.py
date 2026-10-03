from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001_add_hunk_after_multiple_deletion_hunks():
    # Two deletion-only hunks followed by one addition-only hunk
    patch_lines = [
        '@@ -1,1 +1,0 @@\n',
        '-deleted line a\n',
        '@@ -2,1 +2,0 @@\n',
        '-deleted line b\n',
        '@@ -3,0 +3,1 @@\n',
        '+added line\n',
    ]

    result = omit_deletion_hunks(patch_lines)

    # The function must return only the addition-containing hunk: header, a blank line, then the '+' line
    expected = '@@ -3,0 +3,1 @@\n\n+added line\n'

    # Primary behavioral oracle: strict equality to the expected addition-only hunk output
    assert result == expected
