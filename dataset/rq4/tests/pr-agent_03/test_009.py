import pytest

from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    """Boundary probe: two consecutive hunks where the first is deletion-only and the second contains additions.

    Invariant (from boundary plan): deletion-only hunks must not appear in the output; only hunks with at least one '+'
    line (their header and lines) may appear. This test constructs a minimal activating patch and asserts the
    externally observable consequence: the output contains the second hunk's header and '+' line and contains neither
    the first hunk's header nor any '-' deletion lines.
    """

    # Hunk headers must match RE_HUNK_HEADER used by the function. Use standard unified-diff header forms.
    first_hunk_header = '@@ -1,1 +1,0 @@\n'
    first_hunk_deletion = '-deleted line\n'

    second_hunk_header = '@@ -2,0 +2,1 @@\n'
    second_hunk_addition = '+added line\n'

    patch_lines = [first_hunk_header, first_hunk_deletion, second_hunk_header, second_hunk_addition]

    result = omit_deletion_hunks(patch_lines)

    # Primary positive expectations: second hunk header and its '+' addition must be present
    assert second_hunk_header.strip() in result, (
        "Expected added hunk header to appear in result but it did not. Result:\n{}".format(result)
    )
    assert '+added line' in result, "Expected added line to appear in result"

    # Negative expectations (the core of this boundary probe): no deletion-only header or '-' lines leaked/merged
    assert first_hunk_header.strip() not in result, (
        "Deletion-only hunk header must not appear in result (no merge). Result:\n{}".format(result)
    )
    assert '-deleted line' not in result, (
        "Deletion-only lines must not appear in result (no leak/merge). Result:\n{}".format(result)
    )
