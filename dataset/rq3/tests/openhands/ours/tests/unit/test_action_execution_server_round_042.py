import asyncio
import importlib
import os
import shutil
from types import SimpleNamespace
import pytest

AES_MOD = importlib.import_module('openhands.runtime.action_execution_server')

# Helpers used across tests
class DummyFileDownloadObs:
    def __init__(self, content: str, file_path: str):
        self.content = content
        self.file_path = file_path

class DummyErrorObs:
    def __init__(self, msg: str):
        self.message = msg


@pytest.mark.asyncio
async def test_browser_none_round_042():
    """If self.browser is None the method should return an ErrorObservation-like object."""
    # Prepare a dummy self with minimal attributes required by the method
    class DummySelf:
        browser = None

    dummy = DummySelf()

    # Patch ErrorObservation to a predictable class
    monkey_mod = AES_MOD
    orig_ErrorObservation = getattr(monkey_mod, 'ErrorObservation')
    monkey_mod.ErrorObservation = DummyErrorObs

    try:
        # call the coroutine without any complex setup
        coro = AES_MOD.ActionExecutor.browse_interactive(dummy, SimpleNamespace())
        res = await coro
        assert isinstance(res, DummyErrorObs)
        assert 'Browser' in res.message or len(res.message) > 0
    finally:
        # restore
        monkey_mod.ErrorObservation = orig_ErrorObservation


@pytest.mark.asyncio
async def test_no_new_download_returns_browser_observation_round_042(tmp_path, monkeypatch):
    """When browse errors but no new file is found, the original browser observation should be returned."""
    # Create a downloads dir with a single file and mark it as already downloaded
    downloads_dir = tmp_path / 'downloads'
    downloads_dir.mkdir()
    existing = downloads_dir / 'already_here.txt'
    existing.write_text('x')

    # Dummy self object
    class DummySelf:
        pass

    dummy = DummySelf()
    dummy.browser = True
    # async no-op ensure ready
    async def _ensure():
        return None
    dummy._ensure_browser_ready = _ensure
    dummy.downloads_directory = str(downloads_dir)
    dummy.downloaded_files = ['already_here.txt']

    # Fake browse returns an observation with error=True
    browser_obs = SimpleNamespace(error=True, info='err')
    monkeypatch.setattr(AES_MOD, 'browse', lambda action, browser, cwd: asyncio.sleep(0, result=browser_obs))

    # call method
    res = await AES_MOD.ActionExecutor.browse_interactive(dummy, SimpleNamespace())

    # should get the same object back (not wrapped into a FileDownloadObservation)
    assert res is browser_obs


@pytest.mark.asyncio
async def test_new_download_with_extension_round_042(tmp_path, monkeypatch):
    """When a new file is detected and puremagic returns a non-empty extension, the result should be a FileDownloadObservation with that extension in the path and content mentioning action.browser_actions."""
    downloads_dir = tmp_path / 'downloads2'
    downloads_dir.mkdir()
    dl_file = downloads_dir / 'downloaded_file'
    dl_file.write_bytes(b'content')

    # Dummy self
    class DummySelf:
        pass

    dummy = DummySelf()
    dummy.browser = True
    async def _ensure():
        return None
    dummy._ensure_browser_ready = _ensure
    dummy.downloads_directory = str(downloads_dir)
    dummy.downloaded_files = []  # empty -> new file detected

    action = SimpleNamespace(browser_actions='click-123')

    # Fake browse returns an observation with error=True
    browser_obs = SimpleNamespace(error=True)
    monkeypatch.setattr(AES_MOD, 'browse', lambda action, browser, cwd: asyncio.sleep(0, result=browser_obs))

    # Patch puremagic.magic_file to return a guess with extension including whitespace
    class Guess:
        def __init__(self, extension):
            self.extension = extension
    monkeypatch.setattr(AES_MOD.puremagic, 'magic_file', lambda path: [Guess(' .pdf ')])

    # Map '/workspace' joins into tmp_path / 'workspace' to avoid touching real root
    orig_join = AES_MOD.os.path.join
    def join_override(*parts):
        if parts[0] == '/workspace':
            # place workspace under tmp_path
            return str(tmp_path / 'workspace' / parts[1])
        return orig_join(*parts)
    monkeypatch.setattr(AES_MOD.os.path, 'join', join_override)

    # Ensure workspace dir exists
    ws_dir = tmp_path / 'workspace'
    ws_dir.mkdir()

    # Use the real shutil.copy for physical copy (module uses AES_MOD.shutil)
    monkeypatch.setattr(AES_MOD, 'shutil', shutil)

    # Patch FileDownloadObservation to our predictable class
    orig_FileDownloadObservation = getattr(AES_MOD, 'FileDownloadObservation')
    monkeypatch.setattr(AES_MOD, 'FileDownloadObservation', DummyFileDownloadObs)

    try:
        res = await AES_MOD.ActionExecutor.browse_interactive(dummy, action)
        # Should be our DummyFileDownloadObs
        assert isinstance(res, DummyFileDownloadObs)
        # file path should be under tmp_path/workspace and include the extension '.pdf'
        assert str(ws_dir) in res.file_path
        assert res.file_path.endswith('.pdf')
        # content should mention action.browser_actions
        assert action.browser_actions in res.content
        # downloaded_files should have been appended with the new file name
        assert 'downloaded_file' in dummy.downloaded_files
    finally:
        # restore
        monkeypatch.setattr(AES_MOD, 'FileDownloadObservation', orig_FileDownloadObservation)
        monkeypatch.setattr(AES_MOD.os.path, 'join', orig_join)


@pytest.mark.asyncio
async def test_new_download_puremagic_raises_round_042(tmp_path, monkeypatch):
    """If puremagic.magic_file raises, the code should still copy and return a FileDownloadObservation without extension."""
    downloads_dir = tmp_path / 'downloads3'
    downloads_dir.mkdir()
    dl_file = downloads_dir / 'downloaded_any'
    dl_file.write_bytes(b'data')

    class DummySelf:
        pass

    dummy = DummySelf()
    dummy.browser = True
    async def _ensure():
        return None
    dummy._ensure_browser_ready = _ensure
    dummy.downloads_directory = str(downloads_dir)
    dummy.downloaded_files = []

    action = SimpleNamespace(browser_actions='act-xyz')
    browser_obs = SimpleNamespace(error=True)
    monkeypatch.setattr(AES_MOD, 'browse', lambda action, browser, cwd: asyncio.sleep(0, result=browser_obs))

    # Make puremagic.magic_file raise
    def raising_magic(path):
        raise RuntimeError('boom')
    monkeypatch.setattr(AES_MOD.puremagic, 'magic_file', raising_magic)

    # Remap workspace to tmp_path/workspace
    orig_join = AES_MOD.os.path.join
    def join_override(*parts):
        if parts[0] == '/workspace':
            return str(tmp_path / 'workspace' / parts[1])
        return orig_join(*parts)
    monkeypatch.setattr(AES_MOD.os.path, 'join', join_override)
    (tmp_path / 'workspace').mkdir()

    # use real shutil for copy
    monkeypatch.setattr(AES_MOD, 'shutil', shutil)

    orig_FileDownloadObservation = getattr(AES_MOD, 'FileDownloadObservation')
    monkeypatch.setattr(AES_MOD, 'FileDownloadObservation', DummyFileDownloadObs)

    try:
        res = await AES_MOD.ActionExecutor.browse_interactive(dummy, action)
        assert isinstance(res, DummyFileDownloadObs)
        # should not have an extension
        assert not os.path.splitext(res.file_path)[1]
        assert action.browser_actions in res.content
        # ensure downloaded_files updated
        assert len(dummy.downloaded_files) == 1
    finally:
        monkeypatch.setattr(AES_MOD, 'FileDownloadObservation', orig_FileDownloadObservation)
        monkeypatch.setattr(AES_MOD.os.path, 'join', orig_join)
