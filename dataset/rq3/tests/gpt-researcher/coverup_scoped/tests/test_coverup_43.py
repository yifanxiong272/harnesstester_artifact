# file: gpt_researcher/document/online_document.py:36-60
# asked: {"lines": [37, 38, 39, 41, 42, 43, 44, 45, 47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60], "branches": [[43, 44], [43, 47]]}
# gained: {"lines": [37, 38, 39, 41, 42, 43, 44, 45, 47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60], "branches": [[43, 44], [43, 47]]}

import os
import aiohttp
import pytest
import tempfile
from types import SimpleNamespace

from gpt_researcher.document.online_document import OnlineDocumentLoader


@pytest.mark.asyncio
async def test_download_success_monkeypatched_session(monkeypatch):
    url = "http://example.com/file.txt"
    content = b"hello world"
    captured = {}

    class DummyResponse:
        def __init__(self, status, content):
            self.status = status
            self._content = content

        async def read(self):
            return self._content

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySession:
        def __init__(self):
            pass

        def get(self, req_url, headers=None, timeout=None):
            # capture that headers were passed correctly and url
            captured['url'] = req_url
            captured['headers'] = headers
            captured['timeout'] = timeout
            return DummyResponse(200, content)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    # monkeypatch aiohttp.ClientSession to our DummySession
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: DummySession())

    loader = OnlineDocumentLoader([])

    # monkeypatch _get_extension and _load_document on the instance
    monkeypatch.setattr(loader, "_get_extension", lambda u: ".txt")

    tmp_paths = []

    async def fake_load_document(file_path, file_extension):
        # ensure the temp file was created and has expected content
        assert file_extension == "txt"
        assert os.path.exists(file_path)
        with open(file_path, "rb") as f:
            data = f.read()
        assert data == content
        tmp_paths.append(file_path)
        # cleanup the temporary file here to avoid leaving files behind
        os.remove(file_path)
        return ["loaded"]

    monkeypatch.setattr(loader, "_load_document", fake_load_document)

    result = await loader._download_and_process(url)
    assert result == ["loaded"]
    assert captured["url"] == url
    assert captured["headers"] == {"User-Agent": "Mozilla/5.0"}
    assert captured["timeout"] == 6
    # ensure file was cleaned up
    assert tmp_paths and not os.path.exists(tmp_paths[0])


@pytest.mark.asyncio
async def test_download_non_200_returns_empty(monkeypatch):
    url = "http://example.com/missing.pdf"

    class DummyResponse:
        def __init__(self, status):
            self.status = status

        async def read(self):
            # should not be called for non-200, but provide anyway
            return b""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySession:
        def get(self, req_url, headers=None, timeout=None):
            return DummyResponse(404)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: DummySession())

    loader = OnlineDocumentLoader([])

    # If _load_document is called it's an error in this test; ensure it is not.
    async def failing_load_document(*args, **kwargs):
        raise AssertionError("_load_document should not be called for non-200 responses")

    monkeypatch.setattr(loader, "_load_document", failing_load_document)
    monkeypatch.setattr(loader, "_get_extension", lambda u: ".pdf")

    result = await loader._download_and_process(url)
    assert result == []


@pytest.mark.asyncio
async def test_download_clienterror_returns_empty(monkeypatch):
    url = "http://example.com/error"

    class DummySession:
        def get(self, req_url, headers=None, timeout=None):
            # simulate aiohttp ClientError being raised when attempting to GET
            raise aiohttp.ClientError("network error")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: DummySession())

    loader = OnlineDocumentLoader([])

    # _load_document should not be invoked
    async def failing_load_document(*args, **kwargs):
        raise AssertionError("_load_document should not be called on ClientError")

    monkeypatch.setattr(loader, "_load_document", failing_load_document)
    monkeypatch.setattr(loader, "_get_extension", lambda u: ".txt")

    result = await loader._download_and_process(url)
    assert result == []


@pytest.mark.asyncio
async def test_download_unexpected_exception_returns_empty(monkeypatch):
    url = "http://example.com/badread"
    # Make response.read raise a generic Exception to hit the generic except branch

    class BadResponse:
        def __init__(self, status):
            self.status = status

        async def read(self):
            raise Exception("boom")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummySession:
        def get(self, req_url, headers=None, timeout=None):
            return BadResponse(200)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(aiohttp, "ClientSession", lambda *args, **kwargs: DummySession())

    loader = OnlineDocumentLoader([])

    # If _load_document were called it would indicate read did not raise; ensure it's not called
    async def failing_load_document(*args, **kwargs):
        raise AssertionError("_load_document should not be called when read() raises")

    monkeypatch.setattr(loader, "_load_document", failing_load_document)
    monkeypatch.setattr(loader, "_get_extension", lambda u: ".txt")

    result = await loader._download_and_process(url)
    assert result == []
