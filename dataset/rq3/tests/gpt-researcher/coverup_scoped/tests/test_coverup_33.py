# file: gpt_researcher/document/document.py:63-92
# asked: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 88, 89, 90, 92], "branches": [[81, 82], [81, 92]]}
# gained: {"lines": [64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 88, 89, 90, 92], "branches": [[81, 82]]}

import pytest
import builtins

# Import the module under test
from gpt_researcher.document import document as doc_module
from gpt_researcher.document.document import DocumentLoader


class DummyLoader:
    def __init__(self, *args, **kwargs):
        # accept any constructor signature used in the real code
        self.args = args
        self.kwargs = kwargs

    def load(self):
        return []


class TextLoaderSuccess(DummyLoader):
    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        self.path = path

    def load(self):
        return [{"page_content": "text content", "metadata": {"source": self.path}}]


class HTMLLoaderRaises(DummyLoader):
    def __init__(self, path, *args, **kwargs):
        super().__init__(path, *args, **kwargs)
        self.path = path

    def load(self):
        raise RuntimeError("html parse failed")


class PyMuPDFLoaderRaises:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("constructor failure for pdf loader")


@pytest.mark.asyncio
async def test_load_document_txt_success(monkeypatch):
    """
    Test that when TextLoader.load() returns data, _load_document returns that data.
    Ensures loader dict is constructed and the correct loader is used.
    """
    # Monkeypatch all loader names used in the module to safe dummy loaders.
    monkeypatch.setattr(doc_module, "PyMuPDFLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "TextLoader", TextLoaderSuccess, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredWordDocumentLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredPowerPointLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredCSVLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredExcelLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredMarkdownLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "BSHTMLLoader", DummyLoader, raising=False)

    dl = DocumentLoader("some/path")
    result = await dl._load_document("some/path/file.txt", "txt")

    assert isinstance(result, list)
    assert result == [{"page_content": "text content", "metadata": {"source": "some/path/file.txt"}}]


@pytest.mark.asyncio
async def test_load_document_html_loader_raises_inner_except(monkeypatch, capsys):
    """
    Test the branch where the loader exists but loader.load() raises an exception.
    This should be caught by the inner except and return an empty list while printing an error.
    """
    # Provide dummy implementations; BSHTMLLoader will raise on load()
    monkeypatch.setattr(doc_module, "PyMuPDFLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "TextLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredWordDocumentLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredPowerPointLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredCSVLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredExcelLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredMarkdownLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "BSHTMLLoader", HTMLLoaderRaises, raising=False)

    dl = DocumentLoader("base")
    result = await dl._load_document("/tmp/test.html", "html")

    captured = capsys.readouterr()
    # Should have printed the inner exception message about failing to load HTML document
    assert "Failed to load HTML document" in captured.out
    assert "html parse failed" in captured.out
    assert result == []


@pytest.mark.asyncio
async def test_load_document_loader_dict_constructor_raises_outer_except(monkeypatch, capsys):
    """
    Test the outer except branch by making one of the loader constructors raise during
    the creation of the loader_dict. This should be caught by the outer except and
    result in an empty list being returned and an error message printed.
    """
    # Make the very first loader constructor (PyMuPDFLoader) raise to trigger outer except
    monkeypatch.setattr(doc_module, "PyMuPDFLoader", PyMuPDFLoaderRaises, raising=False)
    # Ensure other names exist so attribute lookup doesn't fail (though construction will not continue)
    monkeypatch.setattr(doc_module, "TextLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredWordDocumentLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredPowerPointLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredCSVLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredExcelLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "UnstructuredMarkdownLoader", DummyLoader, raising=False)
    monkeypatch.setattr(doc_module, "BSHTMLLoader", DummyLoader, raising=False)

    dl = DocumentLoader("base")
    result = await dl._load_document("/tmp/fake.pdf", "pdf")

    captured = capsys.readouterr()
    assert "Failed to load document" in captured.out
    assert "constructor failure for pdf loader" in captured.out
    assert result == []
