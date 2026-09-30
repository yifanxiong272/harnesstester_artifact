import importlib
import sys
import types
import pytest

# Helper to inject a fake langchain_community.document_loaders module so importing
# gpt_researcher.document.document does not require the real external package.
def inject_fake_loaders(overrides=None):
    overrides = overrides or {}
    mod = types.ModuleType("langchain_community.document_loaders")

    # Default simple loader class: stores path and optional mode, returns [] by default
    class DefaultLoader:
        def __init__(self, file_path, mode=None):
            self.file_path = file_path

        def load(self):
            return []

    # Provide all expected names; allow overrides to customize behavior per test
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
        setattr(mod, name, overrides.get(name, DefaultLoader))

    sys.modules["langchain_community.document_loaders"] = mod
    return mod


@pytest.mark.asyncio
async def test_html_loader_raises_round_085(capsys):
    # BSHTMLLoader.load will raise -> inner except should catch and print HTML-specific message
    class RaisingHTMLLoader:
        def __init__(self, file_path, mode=None):
            self.file_path = file_path

        def load(self):
            raise RuntimeError("boom-html")

    inject_fake_loaders({"BSHTMLLoader": RaisingHTMLLoader})

    # Import the module under test after injecting fake loaders
    mod = importlib.import_module("gpt_researcher.document.document")
    importlib.reload(mod)

    DocumentLoader = mod.DocumentLoader
    loader = DocumentLoader("dummy")

    ret = await loader._load_document("some-file.html", "html")

    captured = capsys.readouterr()
    # Expect the inner except path: loader present but .load() raised
    assert ret == [], "On loader.load exception we should return the initial empty list"
    assert "Failed to load HTML document : some-file.html" in captured.out
    assert "boom-html" in captured.out


@pytest.mark.asyncio
async def test_html_loader_success_round_085():
    # BSHTMLLoader.load returns a meaningful list -> should be returned unchanged
    class SuccessHTMLLoader:
        def __init__(self, file_path, mode=None):
            self.file_path = file_path

        def load(self):
            return [{"source": self.file_path, "pages": 1}]

    inject_fake_loaders({"BSHTMLLoader": SuccessHTMLLoader})
    mod = importlib.import_module("gpt_researcher.document.document")
    importlib.reload(mod)

    DocumentLoader = mod.DocumentLoader
    loader = DocumentLoader("dummy")

    ret = await loader._load_document("ok-file.html", "html")
    assert ret == [{"source": "ok-file.html", "pages": 1}]


@pytest.mark.asyncio
async def test_unsupported_extension_returns_empty_round_085():
    # No loader for this extension -> loader is None branch -> return empty list
    inject_fake_loaders()  # defaults provided
    mod = importlib.import_module("gpt_researcher.document.document")
    importlib.reload(mod)

    DocumentLoader = mod.DocumentLoader
    loader = DocumentLoader("dummy")

    ret = await loader._load_document("file.unknown", "unknown_ext")
    assert ret == []


@pytest.mark.asyncio
async def test_constructor_raises_triggers_outer_except_round_085(capsys):
    # Make one of the loader constructors raise when called while building loader_dict.
    def raising_constructor(file_path, mode=None):
        raise ValueError("ctor-failed")

    # Inject defaults first, then we'll replace the symbol on the imported module
    inject_fake_loaders()
    mod = importlib.import_module("gpt_researcher.document.document")
    importlib.reload(mod)

    # Patch the module-level name where _load_document will resolve it
    setattr(mod, "PyMuPDFLoader", raising_constructor)

    DocumentLoader = mod.DocumentLoader
    loader = DocumentLoader("dummy")

    ret = await loader._load_document("bad.pdf", "pdf")

    captured = capsys.readouterr()
    # Outer except should catch the constructor error and print a failure message
    assert ret == []
    assert "Failed to load document : bad.pdf" in captured.out
    assert "ctor-failed" in captured.out
