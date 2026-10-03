from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001_deletion_then_addition_no_deletion_leak():
    # Deletion-only hunk immediately followed by an addition-only hunk (no context lines between)
    del_header = '@@ -1,1 +1,0 @@\n'
    del_line = '-deleted line A\n'

    add_header = '@@ -2,0 +2,1 @@\n'
    add_line = '+added line B\n'

    patch_lines = [del_header, del_line, add_header, add_line]

    result = omit_deletion_hunks(patch_lines)
    # Interpret the returned string as logical lines for robust checks
    returned_lines = result.splitlines()

    # Primary oracle combined into a single assertion:
    # - there is at least one hunk header present
    # - there is at least one added line present
    # - there are no deletion lines present
    assert (any(l.startswith('@@') for l in returned_lines)
            and any(l.startswith('+') for l in returned_lines)
            and all(not l.startswith('-') for l in returned_lines)), (
        'omit_deletion_hunks should include the addition hunk and its +line but must not include any -lines. '
        f'Got:\n{result!r}'
    )
