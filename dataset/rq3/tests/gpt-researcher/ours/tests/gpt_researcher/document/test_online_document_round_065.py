import os
import asyncio
import pytest

from gpt_researcher.document import online_document
from gpt_researcher.document.online_document import OnlineDocumentLoader


class _DummyResponse:
    def __init__(self, status=200, content=b""):
        self.status = status
        self._content = content

    async def read(self):
        return self._content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummyGetCtx:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummySession:
    def __init__(self, response):
        self._response = response
        self.last_call = {}

    def get(self, url, headers=None, timeout=None):
        # record the call for later assertions
        self.last_call['url'] = url
        self.last_call['headers'] = headers
        self.last_call['timeout'] = timeout
        return _DummyGetCtx(self._response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_download_and_process_non_200_round_065(monkeypatch, capsys):
    """
    When the HTTP response status is not 200 the method should print a failure
    message and return an empty list.
    """
    # Arrange: create a dummy response with non-200 status
    dummy_resp = _DummyResponse(status=404, content=b"not used")
    dummy_session = _DummySession(dummy_resp)

    # Patch the module-level aiohttp.ClientSession used by the loader
    monkeypatch.setattr(
        'gpt_researcher.document.online_document.aiohttp.ClientSession',
        lambda *a, **k: dummy_session,
        raising=True,
    )

    loader = OnlineDocumentLoader(urls=[])  # constructor exists; pass empty list

    # Act
    result = await loader._download_and_process('http://example.com/missing')

    # Assert
    captured = capsys.readouterr()
    assert result == []
    # The code prints a specific failure message containing the URL and status
    assert "Failed to download http://example.com/missing: HTTP 404" in captured.out


@pytest.mark.asyncio
async def test_download_and_process_success_round_065(monkeypatch):
    """
    When the HTTP response status is 200 the method should read the content,
    write a temp file with the bytes, call _load_document with the temp path and
    extension (without the dot), and return whatever _load_document returns.
    Also verify that the request used the expected headers and timeout.
    """
    # prepare content that will be written to the temp file
    content_bytes = b"hello world"
    dummy_resp = _DummyResponse(status=200, content=content_bytes)
    dummy_session = _DummySession(dummy_resp)

    # Patch the ClientSession to return our dummy session
    monkeypatch.setattr(
        'gpt_researcher.document.online_document.aiohttp.ClientSession',
        lambda *a, **k: dummy_session,
        raising=True,
    )

    # Capture values passed into the fake _load_document
    captured = {}

    async def fake_load_document(self, file_path, file_extension):
        # Record the inputs so we can assert about them
        captured['file_path'] = file_path
        captured['file_extension'] = file_extension
        # Ensure the temp file was actually written with the expected bytes
        with open(file_path, 'rb') as fh:
            captured['file_contents'] = fh.read()
        # Clean up the temp file to leave no residue
        try:
            os.remove(file_path)
        except Exception:
            pass
        return ['LOADED_DOC']

    # Patch the loader's _load_document at the class level
    monkeypatch.setattr(
        online_document.OnlineDocumentLoader,
        '_load_document',
        fake_load_document,
        raising=True,
    )

    # We also patch _get_extension to return the extension with a leading dot
    # so that code path with .strip('.') yields the expected value
    loader = OnlineDocumentLoader(urls=[])
    monkeypatch.setattr(loader, '_get_extension', lambda url: '.txt')

    # Act
    result = await loader._download_and_process('http://example.com/file.txt')

    # Assert returned value comes from our fake load routine
    assert result == ['LOADED_DOC']

    # The fake session should have recorded the headers and timeout used in the call
    assert dummy_session.last_call['url'] == 'http://example.com/file.txt'
    assert isinstance(dummy_session.last_call['headers'], dict)
    assert dummy_session.last_call['headers'].get('User-Agent') == 'Mozilla/5.0'
    assert dummy_session.last_call['timeout'] == 6

    # The fake_load_document should have been invoked with the expected extension
    assert captured['file_extension'] == 'txt'
    # Verify the file contents are exactly what the response provided
    assert captured['file_contents'] == content_bytes
