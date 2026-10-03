def test_probe_001_omit_deletion_hunks_no_deletion_leak():
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Two consecutive hunks: first is deletion-only, second is addition-only.
    patch_lines = [
        '@@ -1,1 +1,0 @@\n',
        '-deleted line A\n',
        '@@ -2,0 +2,1 @@\n',
        '+added line B\n',
    ]

    result = omit_deletion_hunks(patch_lines)

    # Primary oracle: no returned line should start with '-' (no deletion lines leaked)
    lines = result.splitlines()
    assert all(not line.startswith('-') for line in lines), "returned patch leaks deletion lines"

    # Observable check (supporting): the addition hunk header and the added line should appear in the output
    assert any(l.startswith('@@ -2,0 +2,1 @@') for l in lines) or '@@ -2,0 +2,1 @@' in result
    assert any(l.startswith('+added line B') for l in lines)
