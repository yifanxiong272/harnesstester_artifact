def test_omit_deletion_hunks_handles_empty_hunk_line_no_indexerror():
    # Import only the single public entrypoint under test
    from pr_agent.algo.git_patch_processing import omit_deletion_hunks

    # Hunk header, an empty (zero-length) line inside the hunk, then an added line to trigger add_hunk logic
    patch_lines = ['@@ -1,2 +1,2 @@\n', '', '+added line\n']

    # Primary behavioral oracle: the call must complete (no IndexError) and return a string
    result = omit_deletion_hunks(patch_lines)
    assert isinstance(result, str)

    # Supporting observable consequence: when the function handles empty lines gracefully, the added line should appear in the output
    assert '+added line' in result
