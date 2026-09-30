def test_probe_001(tmp_path):
    import asyncio
    from opendevin.action.fileop import FileWriteAction

    # Prepare a fresh path that does not exist so the implementation uses mode 'w'
    target_path = tmp_path / "newfile.txt"
    assert not target_path.exists()

    # Construct instance deterministically without invoking unknown __init__
    fw = object.__new__(FileWriteAction)
    fw.path = str(target_path)
    fw.content = 'a\nb'
    fw.start = 0
    fw.end = -1

    # Execute the async entrypoint synchronously for pytest
    obs = asyncio.run(fw.run(None))

    # Inspect on-disk result
    written = target_path.read_text(encoding='utf-8')

    # Primary behavioral oracle: newline must be preserved between 'a' and 'b'
    assert '\n' in written, f"expected newline in file content, got: {written!r}"
