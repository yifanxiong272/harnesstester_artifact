from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_omit_deletion_hunks_preserves_multi_add_hunk_no_deletion_leak():
    """Boundary: boundary-001

    Construct a patch with three hunks in sequence:
    - first hunk: deletion-only
    - second hunk: contains context lines and multiple '+' addition lines (the target to preserve)
    - third hunk: deletion-only

    Primary oracle (single assertion): the output must include the middle hunk header, include both '+' lines in order,
    and include no '-' (deletion) lines from the surrounding hunks.
    """

    patch_lines = [
        '@@ -1,2 +1,0 @@\n',
        '-deleted1\n',
        '-deleted2\n',
        '@@ -3,0 +3,3 @@\n',
        ' context line A\n',
        '+added one\n',
        '+added two\n',
        ' context line B\n',
        '@@ -6,2 +9,0 @@\n',
        '-deleted3\n',
        '-deleted4\n',
    ]

    out = omit_deletion_hunks(patch_lines)

    # Primary composite assertion: header present, no deletion lines, and both additions present in order.
    assert ('@@ -3,0 +3,3 @@' in out) and (not any(l.startswith('-') for l in out.splitlines())) and (out.splitlines().index('+added one') < out.splitlines().index('+added two'))
