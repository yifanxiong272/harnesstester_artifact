# file: gpt_researcher/document/online_document.py:36-60
# asked: {"lines": [37, 38, 39, 41, 42, 43, 44, 45, 47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60], "branches": [[43, 44], [43, 47]]}
# gained: {"lines": [37, 38, 39, 41, 42, 43, 44, 45, 47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60], "branches": [[43, 44], [43, 47]]}

import os
import aiohttp
import pytest

from gpt_researcher.document.online_document import OnlineDocumentLoader


class FakeResponse:
    def __init__(self, status=200, content=b"", read_exc=None):
        self.status = status
        self._content = content
        self._read_exc = read_exc

    async def read(self):
        if self._read_exc:
            raise self._read_exc
        return self._content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, response=None, get_exc=None):
        self._response = response
        self._get_exc = get_exc

    def get(self, *args, **kwargs):
        if self._get_exc:
            raise self._get_exc
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_download_and_process_success(monkeypatch):
    # Arrange
    content_bytes = b"hello world"
    fake_response = FakeResponse(status=200, content=content_bytes)
    fake_session = FakeSession(response=fake_response)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: fake_session)

    loader = OnlineDocumentLoader(urls=["http://example.com/test.txt"])
    monkeypatch.setattr(loader, "_get_extension", lambda url: ".txt")

    async def fake_load_document(file_path, file_extension):
        assert os.path.exists(file_path), "Temporary file not created"
        with open(file_path, "rb") as f:
            data = f.read()
        assert data == content_bytes
        os.remove(file_path)
        return [{"source": file_path, "ext": file_extension}]

    monkeypatch.setattr(loader, "_load_document", fake_load_document)

    # Act
    result = await loader._download_and_process("http://example.com/test.txt")

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["ext"] == "txt"
    assert isinstance(result[0]["source"], str)


@pytest.mark.asyncio
async def test_download_and_process_non_200(monkeypatch):
    fake_response = FakeResponse(status=404, content=b"not found")
    fake_session = FakeSession(response=fake_response)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: fake_session)

    loader = OnlineDocumentLoader(urls=[])
    monkeypatch.setattr(loader, "_get_extension", lambda url: ".txt")

    result = await loader._download_and_process("http://example.com/missing.txt")
    assert result == []


@pytest.mark.asyncio
async def test_download_and_process_client_error(monkeypatch):
    client_error = aiohttp.ClientError("connection failed")
    fake_session = FakeSession(get_exc=client_error)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: fake_session)

    loader = OnlineDocumentLoader(urls=[])
    monkeypatch.setattr(loader, "_get_extension", lambda url: ".txt")

    result = await loader._download_and_process("http://example.com/error.txt")
    assert result == []


@pytest.mark.asyncio
async def test_download_and_process_unexpected_exception(monkeypatch):
    read_exc = ValueError("bad read")
    fake_response = FakeResponse(status=200, read_exc=read_exc)
    fake_session = FakeSession(response=fake_response)
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: fake_session)

    loader = OnlineDocumentLoader(urls=[])
    monkeypatch.setattr(loader, "_get_extension", lambda url: ".txt")

    result = await loader._download_and_process("http://example.com/badread.txt")
    assert result == []
