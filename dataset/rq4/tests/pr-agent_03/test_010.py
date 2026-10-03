def test_probe_001():
    """Probe mixed newline-termination across adjacent hunks.

    Activation per boundary plan:
    - First hunk header and deletion line lack trailing '\n'.
    - Second hunk header and '+' line include trailing '\n'.

    Primary oracle: return value equals the expected preserved added-hunk string.
    """

    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Construct input with mixed newline termination as specified by the boundary plan
    patch_lines = [
        '@@ -1,1 +1,0 @@',    # header WITHOUT trailing newline
        '-deleted line',      # deletion line WITHOUT trailing newline (deletion-only hunk)
        '@@ -2,0 +2,1 @@\n',  # header WITH trailing newline
        '+added line\n'       # added line WITH trailing newline
    ]

    expected_output = '@@ -2,0 +2,1 @@\n\n+added line\n'

    result = omit_deletion_hunks(patch_lines)

    # Primary behavioral oracle (the one assertion this test stands or falls on)
    assert result == expected_output

    # Extra observable checks (supporting, non-primary): ensure deletion-only content did not leak
    assert '-deleted line' not in result
    # Ensure preserved header appears before the added line
    assert result.find('@@ -2,0 +2,1 @@') != -1 and result.find('+added line') > result.find('@@ -2,0 +2,1 @@')
