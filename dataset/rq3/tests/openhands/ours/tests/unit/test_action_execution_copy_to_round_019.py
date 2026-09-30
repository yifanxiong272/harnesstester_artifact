import os
import tempfile
import shutil
from types import SimpleNamespace
import builtins

import pytest

from openhands.runtime.impl.action_execution import action_execution_client as aec

# We'll reuse the unbound copy_to function so we don't need to construct the full ActionExecutionClient
copy_to_fn = aec.ActionExecutionClient.copy_to


class DummyClient:
    def __init__(self, url="http://server"):
        self.action_execution_server_url = url
        self._sent_requests = []
        self.logs = []

    def _send_action_server_request(self, method, url, **kwargs):
        # record call and return a simple object with .text used by the code
        self._sent_requests.append((method, url, kwargs))
        return SimpleNamespace(text="MOCK_RESPONSE")

    def log(self, level, message):
        # collect logs for assertions
        self.logs.append((level, message))


def test_copy_to_file_not_found_round_019():
    dummy = DummyClient()
    # use a definitely-nonexistent path
    missing_path = "/this/path/does/not/exist_hopefully_12345"
    # Ensure it doesn't exist on the system running tests
    assert not os.path.exists(missing_path)

    with pytest.raises(FileNotFoundError):
        copy_to_fn(dummy, missing_path, "dest", recursive=False)


def test_copy_to_non_recursive_round_019(tmp_path):
    # create a real temporary file to trigger non-recursive upload
    file_path = tmp_path / "afile.txt"
    file_path.write_text("hello")

    dummy = DummyClient()

    # Call the function; this should open the file, call _send_action_server_request and then close the file
    copy_to_fn(dummy, str(file_path), "runtime_dest", recursive=False)

    # Verify that a request was sent and that it used the upload endpoint
    assert len(dummy._sent_requests) == 1
    method, url, kwargs = dummy._sent_requests[0]
    assert method == "POST"
    assert url.endswith("/upload_file")

    # The file object should have been passed under 'files' and closed after use
    files = kwargs.get("files")
    assert isinstance(files, dict)
    fobj = files.get("file")
    # The code closes the file; closed attribute should be True
    assert getattr(fobj, "closed", True)

    # Ensure we logged the completion message containing the response text
    joined_logs = "\n".join([m for _, m in dummy.logs])
    assert "MOCK_RESPONSE" in joined_logs


def test_copy_to_recursive_zip_failure_round_019(tmp_path, monkeypatch):
    # Create a folder with files to be zipped
    src_dir = tmp_path / "somedir"
    src_dir.mkdir()
    f1 = src_dir / "one.txt"
    f1.write_text("1")
    f2 = src_dir / "two.txt"
    f2.write_text("2")

    dummy = DummyClient()

    # Keep track of whether unlink was called with the temp path
    unlink_calls = []

    def fake_unlink(path):
        unlink_calls.append(path)
        # actually remove the file if it exists
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    # Patch unlink used by the module
    monkeypatch.setattr(aec.os, "unlink", fake_unlink)

    # Patch ZipFile in module to raise when write is called to exercise the inner except cleanup
    class FakeZipWriter:
        def write(self, *args, **kwargs):
            raise RuntimeError("zip write failed")

    class FakeZipCtx:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return FakeZipWriter()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(aec, "ZipFile", FakeZipCtx)

    # Use the real NamedTemporaryFile so that a temp file path exists and will be cleaned up
    # No need to patch NamedTemporaryFile here

    # Expect RuntimeError to propagate (the code re-raises the exception after cleanup)
    with pytest.raises(RuntimeError, match="zip write failed"):
        copy_to_fn(dummy, str(src_dir), "dest_dir", recursive=True)

    # Because zipping failed, the module should have attempted to unlink the temp file
    # There should be at least one unlink attempt
    assert len(unlink_calls) >= 1


def test_copy_to_recursive_unlink_error_round_019(tmp_path, monkeypatch):
    # Create a folder with files to be zipped
    src_dir = tmp_path / "somedir2"
    src_dir.mkdir()
    (src_dir / "one.txt").write_text("1")

    dummy = DummyClient()

    # Patch os.unlink to raise when called to force the final cleanup exception path
    def raising_unlink(path):
        raise OSError("boom unlink")

    monkeypatch.setattr(aec.os, "unlink", raising_unlink)

    # Patch ZipFile in module to the real zipfile.ZipFile so zipping succeeds
    # We'll use the module's originally imported ZipFile symbol if available
    # If not, import zipfile.ZipFile directly
    import zipfile

    monkeypatch.setattr(aec, "ZipFile", zipfile.ZipFile)

    # Call copy_to; unlink will raise but should be caught and an error logged
    copy_to_fn(dummy, str(src_dir), "dest_unlink_error", recursive=True)

    # The client should have logged an error regarding failure to delete the temp zip file
    error_logs = [msg for lvl, msg in dummy.logs if lvl == "error"]
    assert any("Failed to delete temporary zip file" in m for m in error_logs)
