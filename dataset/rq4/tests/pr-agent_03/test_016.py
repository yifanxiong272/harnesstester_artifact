from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_omit_deletion_hunks_hunk_count_preservation():
    """Boundary: boundary-001

    Construct two successive hunks where the first contains only deletions and the
    second contains only additions. The invariant under test: the output must
    contain exactly one hunk header (for the add-containing hunk) and must not
    contain any deletion lines (lines beginning with '-').
    """

    # First hunk: deletion-only
    hunk1_header = '@@ -1,1 +1,0 @@\n'
    hunk1_line = '-deleted line\n'

    # Second hunk: addition-only
    hunk2_header = '@@ -2,0 +2,1 @@\n'
    hunk2_line = '+added line\n'

    patch_lines = [
        hunk1_header,
        hunk1_line,
        hunk2_header,
        hunk2_line,
    ]

    out = omit_deletion_hunks(patch_lines)

    # Lines in the output
    out_lines = out.splitlines()

    # Count hunk headers in output (lines that start with '@@')
    header_lines = [l for l in out_lines if l.startswith('@@')]

    # Determine how many input hunks contain at least one '+' line (expected headers)
    expected_add_hunks = 0
    current_hunk_has_plus = False
    for line in patch_lines:
        if line.startswith('@@'):
            if current_hunk_has_plus:
                expected_add_hunks += 1
            current_hunk_has_plus = False
        else:
            if line and line[0] == '+':
                current_hunk_has_plus = True
    # account for last hunk
    if current_hunk_has_plus:
        expected_add_hunks += 1

    assert len(header_lines) == expected_add_hunks, (
        f"expected {expected_add_hunks} hunk header(s) in output, got {len(header_lines)}; output={out!r}"
    )

    # The added line must appear
    assert any(l.startswith('+') for l in out_lines), f"expected added lines in output, got: {out!r}"

    # No output line should begin with '-' (no deletion lines emitted)
    deleted_lines = [l for l in out_lines if l.startswith('-')]
    assert not deleted_lines, f"deletion lines leaked into output: {deleted_lines!r}; full output={out!r}"
