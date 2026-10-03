from aider.coders.udiff_coder import process_fenced_block


def test_probe_001_consistent_filename_normalization():
    """
    Construct a fenced diff block containing two file hunks. The first hunk uses
    initial headers with '--- a/...' and '+++ b/...', which triggers the
    initial normalization branch. The second hunk appears later in the same
    fenced block and is introduced by another '--- a/...' followed by
    '+++ b/...', which exercises the in-loop '+++ ' handling path.

    The invariant: every filename returned in edits must be normalized (no
    leading 'a/' or 'b/'). This test fails if any edit filename still carries
    a git prefix for any hunk.
    """

    # Deterministic fenced diff block lines (start_line_num = 0)
    lines = [
        "--- a/file1\n",      # initial a/ header
        "+++ b/file1\n",      # initial b/ header -> initial normalization should strip 'b/'
        "@@ ... @@\n",
        "-Original\n",
        "+Modified\n",
        "\n",
        "--- a/file2\n",      # subsequent hunk a/ header inside same fenced block
        "+++ b/file2\n",      # subsequent b/ header that the in-loop parsing may not strip
        "@@ ... @@\n",
        "-SecondOld\n",
        "+SecondNew\n",
        "```\n",              # closing fence to terminate block scanning
    ]

    # Call the targeted public entrypoint
    next_idx, edits = process_fenced_block(lines, 0)

    # Basic sanity: two hunks should be discovered
    assert len(edits) == 2, f"Expected 2 edits (hunks), got {len(edits)}: {edits}"

    # Extract filenames as observed by the function
    filenames = [e[0] for e in edits]

    # Primary oracle: no filename should retain a git-side prefix 'a/' or 'b/'
    assert all(
        not (fn.startswith("a/") or fn.startswith("b/"))
        for fn in filenames
    ), f"Found non-normalized filenames: {filenames}"

    # Conservative additional check: filenames should match the expected repository paths
    assert filenames == ["file1", "file2"], f"Filenames not normalized as expected: {filenames}"
