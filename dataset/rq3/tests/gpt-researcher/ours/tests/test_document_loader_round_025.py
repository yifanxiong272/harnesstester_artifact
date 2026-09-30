import asyncio
import os
import pytest
from gpt_researcher.document.document import DocumentLoader


class _FakePage:
    def __init__(self, content, source):
        self.page_content = content
        self.metadata = {"source": source}


@pytest.mark.asyncio
async def test_list_path_success_round_025(tmp_path, monkeypatch):
    # Create a real file so os.path.isfile returns True for it
    f = tmp_path / "doc1.TXT"
    f.write_text("ignored")

    # Prepare loader with a list path containing our real file and a non-existent file
    loader = DocumentLoader([str(f)])

    # Patch _load_document to return a predictable Page-like object
    async def fake_load(self, file_path, file_extension):
        # ensure the extension was normalized to lower-case without dot
        assert file_extension == "txt"
        # Return a single-page list as the real loader would
        return [_FakePage("page content", file_path)]

    monkeypatch.setattr(DocumentLoader, "_load_document", fake_load)

    docs = await loader.load()

    # Expect one document produced from our single file
    assert isinstance(docs, list)
    assert docs == [{"raw_content": "page content", "url": os.path.basename(str(f))}]


@pytest.mark.asyncio
async def test_list_path_empty_results_raise_round_025(monkeypatch):
    # Path list with only non-existent path; os.path.isfile will be False -> no tasks
    loader = DocumentLoader(["/this/path/does/not/exist.txt"])

    # Ensure any accidental call to _load_document would fail test
    async def fake_load_should_not_be_called(self, file_path, file_extension):
        raise AssertionError("_load_document should not be called when files are missing")

    monkeypatch.setattr(DocumentLoader, "_load_document", fake_load_should_not_be_called)

    with pytest.raises(ValueError) as excinfo:
        await loader.load()

    # The loader raises a specific message when no docs loaded
    assert "Failed to load any documents" in str(excinfo.value)


@pytest.mark.asyncio
async def test_walk_path_multiple_files_round_025(tmp_path, monkeypatch):
    # Create a directory with multiple files (different extensions and casing)
    d = tmp_path / "subdir"
    d.mkdir()
    f1 = d / "one.md"
    f1.write_text("ignored")
    f2 = d / "two.PDF"
    f2.write_text("ignored")

    # Provide a directory path (string) so code enters os.walk branch
    loader = DocumentLoader(str(d))

    seen_calls = []

    async def fake_load(self, file_path, file_extension):
        # Record the normalized extension
        seen_calls.append((os.path.basename(file_path), file_extension))
        # Return one page per file
        return [_FakePage(f"content for {file_path}", file_path)]

    monkeypatch.setattr(DocumentLoader, "_load_document", fake_load)

    docs = await loader.load()

    # We should get two docs, one per file
    assert len(docs) == 2
    # Check that extensions were normalized to lower-case without dot
    extensions = {ext for (_, ext) in seen_calls}
    assert "md" in extensions and "pdf" in extensions
    # Ensure URL (basename) returned for each doc
    returned_urls = {doc["url"] for doc in docs}
    expected_basenames = {os.path.basename(str(f1)), os.path.basename(str(f2))}
    assert returned_urls == expected_basenames


def test_invalid_type_raises_round_025():
    # Provide an invalid type (int) to exercise the ValueError branch
    loader = DocumentLoader(123)

    # Since load is async, run it synchronously in the event loop
    async def run():
        return await loader.load()

    with pytest.raises(ValueError) as excinfo:
        asyncio.get_event_loop().run_until_complete(run())

    assert "Invalid type for path" in str(excinfo.value)
