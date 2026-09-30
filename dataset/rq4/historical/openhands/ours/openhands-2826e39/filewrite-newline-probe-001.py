import os
import tempfile
import asyncio
import opendevin.action.fileop as fileop

def test_probe_001():
    # Arrange: prepare a temp directory and deterministically force resolve_path to our target file
    tempdir = tempfile.TemporaryDirectory()
    try:
        target_path = os.path.join(tempdir.name, "test_file.txt")
        orig_resolve = getattr(fileop, "resolve_path")
        # deterministic mapping: whatever path is provided, return our chosen target_path
        fileop.resolve_path = lambda p: target_path

        # Construct a minimal 'self' object with the attributes the entrypoint reads
        class Dummy:
            pass

        dummy = Dummy()
        # Content has multiple logical lines separated by '\n' and does NOT end with a trailing newline
        dummy.content = "line1\nline2"
        dummy.path = "ignored"
        dummy.start = 0
        dummy.end = -1

        # Precondition: ensure the file does not exist (forces mode 'w' in the implementation)
        if os.path.exists(target_path):
            os.remove(target_path)

        # Act: call the async entrypoint directly
        asyncio.run(fileop.FileWriteAction.run(dummy, None))

        # Assert: on-disk file must have each logical line terminated with a '\n'
        with open(target_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        logical_lines = dummy.content.split("\n")
        file_lines = file_content.splitlines(keepends=True)

        # Primary oracle: same count and every written entry ends with '\n'
        assert len(file_lines) == len(logical_lines), (
            "Number of newline-terminated lines on disk does not match logical input lines",
        )
        assert all(line.endswith("\n") for line in file_lines), (
            "Not every logical line was written with a terminating newline on disk",
        )

    finally:
        # Restore monkeypatch and cleanup
        try:
            fileop.resolve_path = orig_resolve
        except Exception:
            pass
        tempdir.cleanup()
