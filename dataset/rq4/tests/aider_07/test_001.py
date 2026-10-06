def test_probe_001():
    # Exercise the public entrypoint only
    from aider.coders.editblock_coder import find_filename

    fence = ('```', '```')
    valid_fnames = ['dir/file3.py']

    # Fenced block markers have leading spaces (boundary condition)
    lines = ['  ```python', 'file3.py', '  ```']

    # Pass a copy so the test's 'lines' variable is not mutated by the implementation
    result = find_filename(list(lines), fence, valid_fnames)

    # Independent oracle: a robust extractor should find the filename despite leading whitespace
    assert result == 'dir/file3.py'
