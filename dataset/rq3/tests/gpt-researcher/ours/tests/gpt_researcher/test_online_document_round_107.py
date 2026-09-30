import asyncio
import importlib
import os
import tempfile
from types import SimpleNamespace

import pytest

# The module under test
module = importlib.import_module("gpt_researcher.document.online_document")
OnlineDocumentLoader = module.OnlineDocumentLoader


def _make_temp_file(contents: bytes = b"dummy"):
    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(contents)
        tf.flush()
        return tf.name
    finally:
        tf.close()


def test_loader_load_success_round_107(monkeypatch):
    # Prepare a fake loader class that will be used for the 'txt' extension
    class FakeTextLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            # return a list to mimic real loader behavior
            return [{"content": "loaded from " + self.file_path}]

    # Spy for os.remove called inside the module under test
    removed = []

    def fake_remove(path):
        removed.append(path)
        # do not delete the file here to allow the test to clean it up deterministically

    # Patch the module-level TextLoader and its os.remove
    monkeypatch.setattr(module, "TextLoader", FakeTextLoader)
    monkeypatch.setattr(module.os, "remove", fake_remove)

    # Create a real temporary file path to pass to the loader
    path = _make_temp_file(b"hello")

    try:
        loader = OnlineDocumentLoader([])
        result = asyncio.run(loader._load_document(path, "txt"))

        # The loader's load() return should be propagated
        assert result == [{"content": "loaded from " + path}]

        # The module's os.remove should have been called with the same path
        assert removed == [path]
    finally:
        # Ensure the filesystem is cleaned up deterministically
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def test_loader_load_raises_round_107(monkeypatch, capsys):
    # Fake loader where load() raises to exercise the exception branch
    class RaisingLoader:
        def __init__(self, file_path):
            self.file_path = file_path

        def load(self):
            raise ValueError("boom")

    removed = []

    def fake_remove(path):
        removed.append(path)

    monkeypatch.setattr(module, "TextLoader", RaisingLoader)
    monkeypatch.setattr(module.os, "remove", fake_remove)

    path = _make_temp_file(b"bad")

    try:
        loader = OnlineDocumentLoader([])
        result = asyncio.run(loader._load_document(path, "txt"))

        # When the loader raises, the function should catch and return an empty list
        assert result == []

        # The exception message and the failure notice should be printed
        captured = capsys.readouterr()
        assert f"Failed to load document : {path}" in captured.out
        assert "boom" in captured.out

        # The finally block should call os.remove with the path
        assert removed == [path]
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
