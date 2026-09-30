# file: gpt_researcher/document/document.py:63-92
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 88, 89, 90, 92], "branches": [[81, 82], [81, 92]]}
# gained: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 88, 89, 90, 92], "branches": [[81, 82], [81, 92]]}

import importlib
import pytest

# Import the module under test
module = importlib.import_module("gpt_researcher.document.document")
DocumentLoader = module.DocumentLoader


class DummyLoader:
    def __init__(self, file_path, *args, **kwargs):
        # accept optional mode kwargs as used by some loaders
        self.file_path = file_path
        self.args = args
        self.kwargs = kwargs

    def load(self):
        # return a distinctive payload so tests can assert on it
        return [f"loaded:{self.file_path}"]


class RaisingLoadMethodLoader(DummyLoader):
    def load(self):
        raise RuntimeError("load failure")


class RaisingConstructorLoader:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("constructor failure")


@pytest.mark.asyncio
async def test_load_document_success_allows_loader_to_return(monkeypatch):
    """
    Ensure that when a loader exists and its load() succeeds, the returned data is propagated.
    This exercises the main happy-path (lines 64-84).
    """
    # Patch all loader names used in the module to DummyLoader so dict creation won't fail.
    names = [
        "PyMuPDFLoader",
        "TextLoader",
        "UnstructuredCSVLoader",
        "UnstructuredExcelLoader",
        "UnstructuredMarkdownLoader",
        "UnstructuredPowerPointLoader",
        "UnstructuredWordDocumentLoader",
        "BSHTMLLoader",
    ]
    for name in names:
        monkeypatch.setattr(module, name, DummyLoader)

    dl = DocumentLoader(path="unused")
    # Test pdf extension
    result = await dl._load_document("some/path/file.pdf", "pdf")
    assert result == ["loaded:some/path/file.pdf"]

    # Test txt extension
    result = await dl._load_document("another/path/file.txt", "txt")
    assert result == ["loaded:another/path/file.txt"]


@pytest.mark.asyncio
async def test_load_document_loader_raises_inner_exception(monkeypatch):
    """
    When the selected loader.load() raises, the exception should be caught and an empty list returned.
    This exercises the inner try/except (lines 82-86).
    """
    # Make all loader constructors succeed, but make BSHTMLLoader.load raise
    monkeypatch.setattr(module, "PyMuPDFLoader", DummyLoader)
    monkeypatch.setattr(module, "TextLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredCSVLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredExcelLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredMarkdownLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredPowerPointLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredWordDocumentLoader", DummyLoader)
    monkeypatch.setattr(module, "BSHTMLLoader", RaisingLoadMethodLoader)

    dl = DocumentLoader(path="unused")
    # Use html extension which maps to BSHTMLLoader whose load raises
    result = await dl._load_document("path/to/bad.html", "html")
    assert result == []


@pytest.mark.asyncio
async def test_load_document_unknown_extension_returns_empty(monkeypatch):
    """
    If the file extension is not in the mapping, loader will be None and the function should return [].
    This exercises the branch where loader is None (line 80-81).
    """
    # Patch loaders to safe DummyLoader so dict creation will not error
    monkeypatch.setattr(module, "PyMuPDFLoader", DummyLoader)
    monkeypatch.setattr(module, "TextLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredCSVLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredExcelLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredMarkdownLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredPowerPointLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredWordDocumentLoader", DummyLoader)
    monkeypatch.setattr(module, "BSHTMLLoader", DummyLoader)

    dl = DocumentLoader(path="unused")
    result = await dl._load_document("file.with.unknownext", "unknownext")
    assert result == []


@pytest.mark.asyncio
async def test_load_document_constructor_raises_outer_exception(monkeypatch):
    """
    Force an exception during the construction of the loader_dict (by having one constructor raise),
    which should be caught by the outer except and result in returning [].
    This exercises the outer except (lines 88-90).
    """
    # Make one of the loader constructors raise at construction time to trigger the outer except.
    monkeypatch.setattr(module, "PyMuPDFLoader", RaisingConstructorLoader)
    # Ensure other constructors are safe so dict literal evaluation still reaches the raising one predictably.
    monkeypatch.setattr(module, "TextLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredCSVLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredExcelLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredMarkdownLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredPowerPointLoader", DummyLoader)
    monkeypatch.setattr(module, "UnstructuredWordDocumentLoader", DummyLoader)
    monkeypatch.setattr(module, "BSHTMLLoader", DummyLoader)

    dl = DocumentLoader(path="unused")
    result = await dl._load_document("some/path/file.pdf", "pdf")
    assert result == []
