# file: openhands/runtime/action_execution_server.py:606-650
# asked: {"lines": [606, 607, 608, 609, 611, 612, 613, 614, 616, 617, 618, 619, 620, 621, 622, 624, 625, 628, 629, 632, 633, 634, 635, 636, 637, 638, 639, 640, 642, 643, 645, 646, 647, 648, 650], "branches": [[607, 608], [607, 611], [613, 614], [613, 616], [618, 619], [618, 624], [619, 618], [619, 620], [624, 625], [624, 628], [635, 636], [635, 642], [637, 638], [637, 642]]}
# gained: {"lines": [606, 607, 608, 609, 611, 612, 613, 614, 616, 617, 618, 619, 620, 621, 622, 624, 625, 628, 629, 632, 633, 634, 635, 636, 637, 638, 639, 640, 642, 643, 645, 646, 647, 648, 650], "branches": [[607, 608], [607, 611], [613, 614], [613, 616], [618, 619], [618, 624], [619, 618], [619, 620], [624, 625], [624, 628], [635, 636], [637, 638]]}

import asyncio
import os
import shutil
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch, tmp_path):
    """
    Patch potentially heavy or environment-dependent components in the
    openhands.runtime.action_execution_server module before constructing
    ActionExecutor instances.
    """
    import importlib
    aes = importlib.import_module("openhands.runtime.action_execution_server")

    # Dummy OHEditor to avoid editor heavy initialization
    class DummyOHEditor:
        def __init__(self, workspace_root=None):
            self.workspace_root = workspace_root

    # Dummy MemoryMonitor to avoid threads/processes
    class DummyMemoryMonitor:
        def __init__(self, enable=False):
            self.enable = enable
            self.started = False

        def start_monitoring(self):
            self.started = True

    # Dummy init_user_and_working_directory (no system user changes)
    def dummy_init_user_and_working_directory(username, user_id, initial_cwd):
        return None

    monkeypatch.setattr(aes, "OHEditor", DummyOHEditor)
    monkeypatch.setattr(aes, "MemoryMonitor", DummyMemoryMonitor)
    monkeypatch.setattr(aes, "init_user_and_working_directory", dummy_init_user_and_working_directory)

    yield


@pytest.mark.asyncio
async def test_browse_interactive_browser_none_returns_error(monkeypatch, tmp_path):
    import importlib
    aes = importlib.import_module("openhands.runtime.action_execution_server")
    from openhands.events.observation import ErrorObservation

    # Create ActionExecutor with patched environment
    execr = aes.ActionExecutor(plugins_to_load=[], work_dir=str(tmp_path), username="u", user_id=1000, enable_browser=True, browsergym_eval_env=None)

    # Ensure browser is None to trigger early error return
    execr.browser = None

    action = SimpleNamespace(browser_actions="do-something")

    obs = await execr.browse_interactive(action)
    assert isinstance(obs, ErrorObservation)
    # ErrorObservation doesn't expose .error; use message or str()
    msg = getattr(obs, "message", None)
    if msg is None:
        s = str(obs)
        assert "Browser functionality is not supported or disabled." in s
    else:
        assert "Browser functionality is not supported or disabled." in msg


@pytest.mark.asyncio
async def test_browse_interactive_returns_browser_observation_when_no_error(monkeypatch, tmp_path):
    import importlib
    aes = importlib.import_module("openhands.runtime.action_execution_server")

    # Instantiate executor
    execr = aes.ActionExecutor(plugins_to_load=[], work_dir=str(tmp_path), username="u", user_id=1000, enable_browser=True, browsergym_eval_env=None)

    # Simulate browser present
    execr.browser = object()

    # Patch _ensure_browser_ready to a no-op async function
    async def _noop():
        return None

    execr._ensure_browser_ready = _noop

    # Patch browse to return an object with error = False
    async def fake_browse(action, browser, initial_cwd):
        return SimpleNamespace(error=False, info="ok")

    monkeypatch.setattr(aes, "browse", fake_browse)

    action = SimpleNamespace(browser_actions="do-something")

    obs = await execr.browse_interactive(action)
    # Should return the same object (or equivalent) from fake_browse
    assert hasattr(obs, "error") and obs.error is False
    assert getattr(obs, "info") == "ok"


@pytest.mark.asyncio
async def test_browse_interactive_error_no_new_download(monkeypatch, tmp_path):
    import importlib
    aes = importlib.import_module("openhands.runtime.action_execution_server")

    execr = aes.ActionExecutor(plugins_to_load=[], work_dir=str(tmp_path), username="u", user_id=1000, enable_browser=True, browsergym_eval_env=None)

    execr.browser = object()
    async def _noop(): return None
    execr._ensure_browser_ready = _noop

    # Prepare downloads directory with one file that is already known
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    file_a = downloads_dir / "a.txt"
    file_a.write_text("hello")
    execr.downloads_directory = str(downloads_dir)
    execr.downloaded_files = ["a.txt"]

    # Patch browse to return an error observation (simulated)
    async def fake_browse(action, browser, initial_cwd):
        return SimpleNamespace(error=True, message="some browser error")

    monkeypatch.setattr(aes, "browse", fake_browse)

    action = SimpleNamespace(browser_actions="try-download")

    obs = await execr.browse_interactive(action)
    # Since there was no new download, should return the browser_observation unchanged
    assert hasattr(obs, "error") and obs.error is True
    assert getattr(obs, "message") == "some browser error"


@pytest.mark.asyncio
async def test_browse_interactive_new_download_with_extension(monkeypatch, tmp_path):
    import importlib
    aes = importlib.import_module("openhands.runtime.action_execution_server")

    execr = aes.ActionExecutor(plugins_to_load=[], work_dir=str(tmp_path), username="u", user_id=1000, enable_browser=True, browsergym_eval_env=None)

    execr.browser = object()
    async def _noop(): return None
    execr._ensure_browser_ready = _noop

    # Create downloads directory and a new file that wasn't seen before
    downloads_dir = tmp_path / "downloads2"
    downloads_dir.mkdir()
    new_file = downloads_dir / "download1.bin"
    new_file.write_bytes(b"\x00\x01\x02")
    execr.downloads_directory = str(downloads_dir)
    execr.downloaded_files = []

    # Patch browse to return an error (so code goes down the download handling path)
    async def fake_browse(action, browser, initial_cwd):
        return SimpleNamespace(error=True)

    monkeypatch.setattr(aes, "browse", fake_browse)

    # Patch puremagic.magic_file to return an object with extension
    def fake_magic_file(path):
        return [SimpleNamespace(extension=".dat")]

    # set puremagic module attribute safely
    monkeypatch.setattr(aes, "puremagic", SimpleNamespace(magic_file=fake_magic_file))

    # Intercept shutil.copy so we don't try to write to literal /workspace path.
    copied = {}

    def fake_copy(src, dst, *, follow_symlinks=True):
        # Record the copy invocation
        copied['src'] = src
        copied['dst'] = dst
        # Instead of writing to dst (which will be under /workspace), create a mapped file under tmp_path
        basename = os.path.basename(dst)
        mapped = tmp_path / "mapped_workspace"
        mapped.mkdir(exist_ok=True)
        (mapped / basename).write_bytes(b"copied")
        return None

    monkeypatch.setattr(shutil, "copy", fake_copy)

    action = SimpleNamespace(browser_actions="download-action")

    obs = await execr.browse_interactive(action)

    # Verify that an observation with file_path attribute was returned
    assert hasattr(obs, "file_path")
    # Should include the extension added by fake_magic_file (.dat)
    assert obs.file_path.endswith(".dat")
    # The executor should have recorded the downloaded file name
    assert execr.downloaded_files and execr.downloaded_files[-1] == "download1.bin"

    # Ensure our fake_copy was invoked with the src that existed in downloads_dir
    assert copied["src"] == os.path.join(str(downloads_dir), "download1.bin")
    assert os.path.basename(copied["dst"]).startswith("file_")


@pytest.mark.asyncio
async def test_browse_interactive_new_download_magic_raises(monkeypatch, tmp_path):
    import importlib
    aes = importlib.import_module("openhands.runtime.action_execution_server")

    execr = aes.ActionExecutor(plugins_to_load=[], work_dir=str(tmp_path), username="u", user_id=1000, enable_browser=True, browsergym_eval_env=None)

    execr.browser = object()
    async def _noop(): return None
    execr._ensure_browser_ready = _noop

    # Create downloads directory and a new file that wasn't seen before
    downloads_dir = tmp_path / "downloads3"
    downloads_dir.mkdir()
    new_file = downloads_dir / "untypedfile"
    new_file.write_bytes(b"\x99")
    execr.downloads_directory = str(downloads_dir)
    execr.downloaded_files = []

    # Patch browse to return an error
    async def fake_browse(action, browser, initial_cwd):
        return SimpleNamespace(error=True)

    monkeypatch.setattr(aes, "browse", fake_browse)

    # Patch puremagic.magic_file to raise an exception to hit the except branch
    def raising_magic(path):
        raise RuntimeError("magic failed")

    monkeypatch.setattr(aes, "puremagic", SimpleNamespace(magic_file=raising_magic))

    # Patch shutil.copy to avoid touching /workspace
    def fake_copy(src, dst, *, follow_symlinks=True):
        # create a mapped file locally
        basename = os.path.basename(dst)
        mapped = tmp_path / "mapped_workspace2"
        mapped.mkdir(exist_ok=True)
        (mapped / basename).write_bytes(b"copied2")
        return None

    monkeypatch.setattr(shutil, "copy", fake_copy)

    action = SimpleNamespace(browser_actions="download-action-2")

    obs = await execr.browse_interactive(action)

    # Should have file_path attribute and no extension appended (magic raised)
    assert hasattr(obs, "file_path")
    assert obs.file_path.endswith("file_1")
    assert execr.downloaded_files and execr.downloaded_files[-1] == "untypedfile"
