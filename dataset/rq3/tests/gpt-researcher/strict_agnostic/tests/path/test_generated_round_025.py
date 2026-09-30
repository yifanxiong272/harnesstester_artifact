import asyncio
import os
import pytest
from gpt_researcher.document.document import DocumentLoader


class _Page:
    """Simple stand-in for the page objects returned by _load_document.
    Mirrors the attributes used by DocumentLoader.load: page_content and metadata['source'].
    """

    def __init__(self, content, source):
        self.page_content = content
        self.metadata = {"source": source}


# Helper factory to create an async stub for _load_document that returns predictable pages
def make_fake_loader(mapping):
    async def _fake(self, file_path, file_extension):
        # Return a shallow copy of the list so tests cannot accidentally mutate shared state
        entries = mapping.get(os.path.basename(file_path), mapping.get(file_path, []))
        # Ensure coroutine returns a list of _Page instances
        return [(_Page(c["content"], c["source"])) for c in entries]

    return _fake


def test_list_path_with_files_round_025(tmp_path, monkeypatch):
    """Covers the branch where path is a list and valid files are included.

    - Ensures os.path.isfile check passes and _load_document is invoked for present files.
    - Ensures pages with falsy page_content are filtered out and only truthy content becomes docs.
    - Verifies url uses os.path.basename(page.metadata['source']).
    """
    # Create two files: one will produce content, the other will produce empty content
    file1 = tmp_path / "file1.TXT"
    file2 = tmp_path / "file2.md"
    file1.write_text("irrelevant")
    file2.write_text("irrelevant")

    # Mapping keyed by basename -> list of page dicts
    mapping = {
        "file1.TXT": [{"content": "CONTENT-1", "source": str(file1)}],
        "file2.md": [{"content": "", "source": str(file2)}],
    }

    monkeypatch.setattr(DocumentLoader, "_load_document", make_fake_loader(mapping))

    loader = DocumentLoader([str(file1), str(file2)])

    docs = asyncio.run(loader.load())

    # Only one doc should be returned because file2's page content is falsy
    assert isinstance(docs, list)
    assert len(docs) == 1

    doc = docs[0]
    assert doc["raw_content"] == "CONTENT-1"
    # url should be os.path.basename(page.metadata['source'])
    assert doc["url"] == os.path.basename(str(file1))


def test_list_path_no_files_raises_round_025(monkeypatch):
    """Covers the case where path is a list but no valid files exist, leading to the "Failed to load any documents!" error.

    - Use an empty list so no tasks are created and the code raises the expected ValueError.
    """
    loader = DocumentLoader([])

    with pytest.raises(ValueError) as excinfo:
        asyncio.run(loader.load())

    assert "Failed to load any documents" in str(excinfo.value)


def test_str_path_walk_round_025(tmp_path, monkeypatch):
    """Covers the branch where path is a string (os.walk) and files in the directory are discovered.

    - Ensures tasks are created from os.walk and that returned pages produce docs.
    """
    # Create a directory with one file
    d = tmp_path / "subdir"
    d.mkdir()
    f = d / "document.PDF"
    f.write_text("dummy")

    # Map by basename so the fake resolver recognizes the file produced by os.walk
    mapping = {
        "document.PDF": [{"content": "PDF-DATA", "source": str(f)}]
    }

    monkeypatch.setattr(DocumentLoader, "_load_document", make_fake_loader(mapping))

    loader = DocumentLoader(str(tmp_path))

    docs = asyncio.run(loader.load())

    assert isinstance(docs, list)
    assert len(docs) == 1
    assert docs[0]["raw_content"] == "PDF-DATA"
    assert docs[0]["url"] == os.path.basename(str(f))


def test_invalid_type_raises_round_025():
    """Covers the else branch where an invalid type for path raises a ValueError.

    - Passing an int should immediately raise a ValueError describing the invalid type.
    """
    loader = DocumentLoader(123)  # invalid type

    with pytest.raises(ValueError) as excinfo:
        asyncio.run(loader.load())

    assert "Invalid type for path" in str(excinfo.value)
