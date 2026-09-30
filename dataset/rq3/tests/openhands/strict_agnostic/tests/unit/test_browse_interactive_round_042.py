import os
from types import SimpleNamespace
import pytest

import openhands.runtime.action_execution_server as aes
from openhands.runtime.action_execution_server import ActionExecutor
from openhands.events.observation import ErrorObservation, FileDownloadObservation


@pytest.mark.asyncio
async def test_browser_none_round_042():
    """
    When self.browser is None the method should immediately return an ErrorObservation.
    """
    # Build a minimal 'self' object with browser set to None.
    dummy = SimpleNamespace()
    dummy.browser = None

    # Call the unbound coroutine with the dummy self and a minimal action object.
    result = await ActionExecutor.browse_interactive(dummy, SimpleNamespace())

    # Observable assertion: we get an ErrorObservation instance.
    assert isinstance(result, ErrorObservation)


@pytest.mark.asyncio
async def test_download_new_file_round_042(tmp_path, monkeypatch):
    """
    Simulate browse returning an error observation and a new file present in downloads_directory.
    This exercises the branch that detects a new download, guesses an extension, and returns
    a FileDownloadObservation while attempting to copy the file.
    """
    # Prepare a fake downloads directory and a file that will be reported as newly downloaded.
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    filename = "downloaded.bin"
    src_path = downloads_dir / filename
    src_path.write_text("dummy")

    # Create a minimal 'self' object with required attributes used by the method.
    dummy = SimpleNamespace()
    dummy.browser = object()  # non-None to avoid the early return
    async def _ensure():
        return None
    dummy._ensure_browser_ready = _ensure
    dummy.initial_cwd = str(tmp_path)
    dummy.downloads_directory = str(downloads_dir)
    dummy.downloaded_files = []

    # Action object with browser_actions string used in the returned message.
    action = SimpleNamespace(browser_actions="CLICK_TEST")

    # Patch the 'browse' symbol imported in the module to return an object with error=True
    async def fake_browse(act, browser, cwd):
        return SimpleNamespace(error=True)
    monkeypatch.setattr(aes, "browse", fake_browse)

    # Patch os.listdir so the code detects the single new file we created.
    monkeypatch.setattr(os, "listdir", lambda path: [filename])

    # Patch puremagic.magic_file to deterministically report an extension.
    monkeypatch.setattr(aes.puremagic, "magic_file", lambda p: [SimpleNamespace(extension=".txt")])

    # Intercept shutil.copy so we don't touch real /workspace. Record the call arguments.
    copied = {}
    def fake_copy(src, dst):
        copied['args'] = (src, dst)
    monkeypatch.setattr(aes.shutil, "copy", fake_copy)

    # Execute the method under test.
    result = await ActionExecutor.browse_interactive(dummy, action)

    # The method should return a FileDownloadObservation and reference the /workspace path
    assert isinstance(result, FileDownloadObservation)

    expected_tgt = os.path.join("/workspace", "file_1.txt")
    # The FileDownloadObservation was constructed with file_path=tgt_path
    assert getattr(result, "file_path") == expected_tgt

    # And our fake copy should have been invoked with the source file and the produced tgt path
    assert copied['args'][0] == os.path.join(str(downloads_dir), filename)
    assert copied['args'][1] == expected_tgt
