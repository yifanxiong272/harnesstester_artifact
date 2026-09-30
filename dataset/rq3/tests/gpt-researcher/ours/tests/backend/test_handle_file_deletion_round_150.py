import os
import pytest
import backend.server.server_utils as su


class DummyJSONResponse:
    """A lightweight stand-in for fastapi.responses.JSONResponse used for testing.

    It preserves the initializer signature used in the source code and exposes
    `.content` and `.status_code` attributes for assertions.
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.content = kwargs.get("content")
        # default status code to 200 when not provided (mimics JSONResponse default)
        self.status_code = kwargs.get("status_code", 200)


@pytest.mark.asyncio
async def test_handle_file_deletion_deleted_round_150(monkeypatch, capsys):
    """Simulate the file-existing branch.

    - Patch module-level JSONResponse to DummyJSONResponse so the test inspects
      the returned object deterministically.
    - Patch os.path.exists to return True for the expected path and record calls
      to os.remove.
    - Assert removal was requested, returned JSON has success message, and
      printed output includes the expected deletion line.
    """
    filename = "some/nested/path/document.md"
    DOC_PATH = "/var/test/docs"

    # compute expected path using the same path operations as the module
    expected_path = su.os.path.join(DOC_PATH, su.os.path.basename(filename))

    removed = {"called": False, "path": None}

    def fake_exists(path):
        # ensure code under test calls exists with the composed path
        assert path == expected_path
        return True

    def fake_remove(path):
        removed["called"] = True
        removed["path"] = path

    # Patch JSONResponse and os functions where server_utils resolves them
    monkeypatch.setattr(su, "JSONResponse", DummyJSONResponse)
    monkeypatch.setattr(su.os.path, "exists", fake_exists)
    monkeypatch.setattr(su.os, "remove", fake_remove)

    # Call the async function under test
    resp = await su.handle_file_deletion(filename, DOC_PATH)

    # Verify the returned response is our dummy and has the expected payload
    assert isinstance(resp, DummyJSONResponse)
    assert resp.content == {"message": "File deleted successfully"}
    assert resp.status_code == 200

    # os.remove should have been called with the expected path
    assert removed["called"] is True
    assert removed["path"] == expected_path

    captured = capsys.readouterr()
    assert f"File deleted: {expected_path}" in captured.out


@pytest.mark.asyncio
async def test_handle_file_deletion_not_found_round_150(monkeypatch, capsys):
    """Simulate the file-missing branch.

    - Patch JSONResponse to DummyJSONResponse.
    - Patch os.path.exists to return False so the 404 branch runs.
    - Ensure os.remove is not called and the returned response has status 404.
    - Assert the printed message indicates the file was not found.
    """
    filename = "another/place/missing.txt"
    DOC_PATH = "/var/test/docs"

    expected_path = su.os.path.join(DOC_PATH, su.os.path.basename(filename))

    remove_called = {"called": False}

    def fake_exists(path):
        assert path == expected_path
        return False

    def fake_remove(path):
        # If called, mark and allow test to assert it shouldn't be
        remove_called["called"] = True

    monkeypatch.setattr(su, "JSONResponse", DummyJSONResponse)
    monkeypatch.setattr(su.os.path, "exists", fake_exists)
    monkeypatch.setattr(su.os, "remove", fake_remove)

    resp = await su.handle_file_deletion(filename, DOC_PATH)

    # Should be DummyJSONResponse with 404 status
    assert isinstance(resp, DummyJSONResponse)
    assert resp.content == {"message": "File not found"}
    assert resp.status_code == 404

    # remove should not have been called
    assert remove_called["called"] is False

    captured = capsys.readouterr()
    assert f"File not found: {expected_path}" in captured.out
