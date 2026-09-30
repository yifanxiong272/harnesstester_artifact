from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    """Probe: calling omit_deletion_hunks with an empty ('') hunk line should not raise IndexError
    and should preserve the added line.
    Activation: input contains a hunk header, a zero-length string, and an added line beginning with '+'.
    Primary oracle: the returned string contains both the hunk header and the added line.
    """
    header = '@@ -1,0 +1,1 @@\n'
    # Construct patch lines per boundary activation: header, an explicit empty-string line, then an added line
    patch_lines = [header, '', '+added line\n']

    # Exercise the public entrypoint directly. If the implementation indexes into the empty string,
    # this call will raise IndexError and the test will fail (revealing the bug).
    result = omit_deletion_hunks(patch_lines)

    # Primary behavioral oracle (single assertion): the header (stripped) must be present and the added line must be preserved
    assert header.strip() in result and '+added line' in result, (
        "omit_deletion_hunks must accept empty hunk lines without raising and must preserve added lines"
    )
