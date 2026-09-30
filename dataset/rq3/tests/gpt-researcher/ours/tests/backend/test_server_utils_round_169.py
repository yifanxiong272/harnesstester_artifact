import io
import os
import asyncio
from pathlib import Path

import backend.server.server_utils as server_utils


class FakeLoader:
    def __init__(self, path):
        # preserve the constructor signature and store provided path
        self.path = path
        self.loaded = False

    async def load(self):
        # async load to match expected contract
        self.loaded = True


def make_upload(filename: str, content: bytes):
    # simple container preserving .filename and .file attributes
    upload = type("Upload", (), {})()
    upload.filename = filename
    upload.file = io.BytesIO(content)
    return upload


def test_handle_file_upload_writes_file_and_calls_loader_round_169(tmp_path, monkeypatch, capsys):
    """
    Exercise the normal path: verify file is written to DOC_PATH, DocumentLoader is constructed
    with DOC_PATH and its async load() is awaited. Also assert the printed message.
    """
    DOC_PATH = str(tmp_path)
    content = b"hello world"
    upload = make_upload("myfile.txt", content)

    created = {}

    def fake_document_loader_ctor(path):
        # preserve the symbol shape and return an object with async load
        inst = FakeLoader(path)
        created['instance'] = inst
        return inst

    # Patch the symbol where the function resolves it
    monkeypatch.setattr(server_utils, "DocumentLoader", fake_document_loader_ctor)

    # Call the async function synchronously using asyncio.run to avoid pytest-asyncio requirement
    result = asyncio.run(server_utils.handle_file_upload(upload, DOC_PATH))

    expected_path = os.path.join(DOC_PATH, os.path.basename(upload.filename))

    # returned shape assertion
    assert result == {"filename": upload.filename, "path": expected_path}

    # file content assertion
    with open(expected_path, "rb") as f:
        assert f.read() == content

    # DocumentLoader usage assertions
    assert 'instance' in created
    assert created['instance'].path == DOC_PATH
    assert created['instance'].loaded is True

    # printed message assertion
    captured = capsys.readouterr()
    assert f"File uploaded to {expected_path}" in captured.out


def test_handle_file_upload_basename_stripping_round_169(tmp_path, monkeypatch):
    """
    Ensure that when upload.filename contains directory components, os.path.basename is used
    so the file is stored under DOC_PATH with only the basename.
    """
    DOC_PATH = str(tmp_path)
    # include path components in the filename to verify basename usage
    filename_with_dirs = "some/odd/dir/name.bin"
    content = b"data"
    upload = make_upload(filename_with_dirs, content)

    created = {}

    def fake_document_loader_ctor(path):
        inst = FakeLoader(path)
        created['instance'] = inst
        return inst

    monkeypatch.setattr(server_utils, "DocumentLoader", fake_document_loader_ctor)

    result = asyncio.run(server_utils.handle_file_upload(upload, DOC_PATH))

    # basename should be used in returned path
    expected_basename = os.path.basename(filename_with_dirs)
    expected_path = os.path.join(DOC_PATH, expected_basename)

    assert result["filename"] == filename_with_dirs
    assert result["path"] == expected_path

    # file exists at expected path and contains expected bytes
    with open(expected_path, "rb") as f:
        assert f.read() == content

    # loader was constructed with DOC_PATH and load awaited
    assert 'instance' in created
    assert created['instance'].path == DOC_PATH
    assert created['instance'].loaded is True
