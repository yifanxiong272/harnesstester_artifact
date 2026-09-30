def test_probe_001():
    # Import the public entrypoint under test
    from aider.coders.udiff_coder import process_fenced_block

    # Construct a deterministic fenced unified-diff block. Use '```diff' and
    # provide start_line_num=1 to match how find_diffs calls process_fenced_block.
    # Include a placeholder empty line so the filename header lands at block[1].
    lines = [
        "```diff",
        "",
        "+++ file.txt",
        "@@ -1,2 +1,2 @@",
        "-",
        "+",
        "```",
    ]

    # Call the target function with start_line_num pointing at the first inner line
    next_index, edits = process_fenced_block(lines, 1)

    # Basic sanity checks on return types
    assert isinstance(next_index, int), "next index should be an int"
    assert isinstance(edits, list), "edits should be a list"

    # Primary oracle: at least one edit's hunk must contain '-' immediately followed by '+'
    found = False
    for fname, hunk in edits:
        # ensure hunk is a sequence we can inspect
        if not isinstance(hunk, list):
            continue
        for i in range(len(hunk) - 1):
            if hunk[i] == "-" and hunk[i + 1] == "+":
                found = True
                break
        if found:
            break

    assert found, f"Expected single-character '-' and '+' lines to be preserved in a hunk, but edits={edits}"
