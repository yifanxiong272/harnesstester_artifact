# file: openhands/runtime/impl/action_execution/action_execution_client.py:193-263
# asked: {"lines": [196, 197, 199, 201, 202, 203, 204, 206, 208, 209, 210, 211, 213, 214, 215, 216, 217, 218, 219, 221, 223, 224, 225, 227, 228, 229, 231, 232, 233, 235, 236, 238, 240, 241, 242, 243, 244, 245, 247, 248, 249, 252, 253, 256, 257, 258, 259, 260, 261, 262], "branches": [[196, 197], [196, 199], [206, 208], [206, 235], [215, 216], [215, 223], [216, 215], [216, 217], [231, 232], [231, 233], [252, 253], [252, 256], [256, 0], [256, 257]]}
# gained: {"lines": [196, 197, 199, 201, 202, 203, 204, 206, 208, 209, 210, 211, 213, 214, 215, 216, 217, 218, 219, 221, 223, 224, 225, 227, 228, 229, 231, 232, 233, 238, 240, 241, 242, 243, 244, 245, 247, 248, 249, 252, 253, 256, 257, 258, 259, 260, 261, 262], "branches": [[196, 197], [196, 199], [206, 208], [215, 216], [215, 223], [216, 215], [216, 217], [231, 232], [252, 253], [252, 256], [256, 0], [256, 257]]}

import os
from types import SimpleNamespace

import pytest

import openhands.runtime.impl.action_execution.action_execution_client as aec


class DummyClient(aec.ActionExecutionClient):
    def __init__(self):
        # do not call super().__init__; keep minimal state required by tests
        self._logged = []
        self._sent = []

    @property
    def action_execution_server_url(self) -> str:
        return "http://fake"

    async def connect(self) -> None:
        # satisfy abstract method
        return None

    def log(self, level, msg):
        self._logged.append((level, msg))

    # default send implementation (can be overridden per-test)
    def _send_action_server_request(self, method, url, **kwargs):
        self._sent.append((method, url, kwargs))
        return SimpleNamespace(text="OK")


def test_copy_to_missing_source_raises_file_not_found():
    client = DummyClient()
    nonexist = "/this/path/should/not/exist_hopefully_12345"
    with pytest.raises(FileNotFoundError) as exc:
        client.copy_to(nonexist, "/dest", recursive=False)
    assert str(exc.value).startswith("Source file")
    assert nonexist in str(exc.value)


def test_copy_to_recursive_creates_zip_and_logs_unlink_error(monkeypatch, tmp_path):
    # Prepare a source directory with a file to be zipped
    src = tmp_path / "srcdir"
    src.mkdir()
    fpath = src / "file.txt"
    fpath.write_text("hello")

    client = DummyClient()

    sent_capture = {}

    def fake_send(method, url, **kwargs):
        # capture the file object passed in
        files = kwargs.get("files", {})
        sent_capture['files'] = files
        # Ensure params recursive is "true"
        params = kwargs.get("params", {})
        assert params.get("recursive") == "true"
        return SimpleNamespace(text="uploaded")

    # attach our fake send to the instance
    client._send_action_server_request = fake_send

    # monkeypatch os.unlink in module to raise to trigger the error logging branch in final cleanup
    def fake_unlink(path):
        raise RuntimeError("unlink failed intentionally for test")

    monkeypatch.setattr(aec.os, "unlink", fake_unlink)

    # Run copy_to; the unlink failure should be caught and logged, not raised
    client.copy_to(str(src), "/remote/dest", recursive=True)

    # Verify that send was called and a file-like object was provided
    assert 'files' in sent_capture
    assert 'file' in sent_capture['files']
    uploaded_file = sent_capture['files']['file']
    # The file should be closed by the method in the finally block
    assert uploaded_file.closed is True

    # Verify that an error log entry was created about failing to delete temp zip
    error_logs = [m for (lvl, m) in client._logged if lvl == 'error']
    assert any("Failed to delete temporary zip file" in m for m in error_logs)


def test_copy_to_recursive_zip_failure_cleans_tempfile(monkeypatch, tmp_path):
    # We'll monkeypatch NamedTemporaryFile and ZipFile in the module to simulate a zip error
    created_tmp = tmp_path / "created_temp.zip"

    class DummyNamedTempFile:
        def __init__(self, suffix=None, delete=False):
            # create the file on disk to simulate the real behavior
            self.name = str(created_tmp)
            with open(self.name, "wb") as fh:
                fh.write(b"")
            self._closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self._closed = True

    class DummyZipFile:
        def __init__(self, path, mode):
            self.path = path

        def __enter__(self):
            # Simulate a failure while zipping
            raise RuntimeError("simulated zip failure")

        def __exit__(self, exc_type, exc, tb):
            return False

    # Patch tempfile.NamedTemporaryFile and ZipFile used in the target module
    monkeypatch.setattr(aec.tempfile, "NamedTemporaryFile", DummyNamedTempFile)
    monkeypatch.setattr(aec, "ZipFile", DummyZipFile)

    # Ensure the src dir exists with at least one file so the code iterates
    src = tmp_path / "src2"
    src.mkdir()
    (src / "a.txt").write_text("data")

    client = DummyClient()

    # Call copy_to and expect the RuntimeError from our DummyZipFile to propagate
    with pytest.raises(RuntimeError) as excinfo:
        client.copy_to(str(src), "/dest", recursive=True)
    assert "simulated zip failure" in str(excinfo.value)

    # After the exception the temp zip file should have been removed by the except cleanup
    assert not created_tmp.exists()
