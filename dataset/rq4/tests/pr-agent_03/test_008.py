from pr_agent.algo.git_patch_processing import omit_deletion_hunks


def test_probe_001():
    # Minimal-form deletion-only hunk (no comma counts) immediately followed by an added hunk.
    patch_lines = [
        "@@ -1 +1 @@\n",
        "-deleted line\n",
        "@@ -2 +2 @@\n",
        "+added line\n",
    ]

    result = omit_deletion_hunks(patch_lines)

    # Primary oracle (one combined assertion):
    # - deletion-only hunk header and its '-' line MUST NOT appear
    # - the added-hunk header and its '+' line MUST appear
    assert (
        "@@ -1 +1 @@" not in result
        and "-deleted line" not in result
        and "@@ -2 +2 @@" in result
        and "+added line" in result
    )
