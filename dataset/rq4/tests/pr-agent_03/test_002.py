from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    # First hunk: deletion-only
    header1 = '@@ -1,1 +1,0 @@\n'
    deleted = '-deleted line\n'

    # Second hunk: contains an addition and should be the only hunk preserved
    header2 = '@@ -2,0 +2,1 @@\n'
    added = '+added line\n'

    patch_lines = [header1, deleted, header2, added]

    result = omit_deletion_hunks(patch_lines)

    # The canonical expected serialization for a single kept hunk (header, blank line, then body)
    expected = header2 + '\n' + added

    # Primary oracle: the output must exactly equal the expected (no leakage of header1/deleted)
    assert result == expected, f"omit_deletion_hunks leaked deletion-only hunk into output: {result!r}"
