# file: gpt_researcher/document/document.py:21-61
# asked: {"lines": [22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 40, 49, 50, 51, 52, 53, 54, 55, 58, 59, 61], "branches": [[23, 24], [23, 31], [24, 25], [24, 49], [25, 24], [25, 26], [31, 32], [31, 40], [32, 33], [32, 49], [33, 32], [33, 34], [50, 51], [50, 58], [51, 50], [51, 52], [52, 51], [52, 53], [58, 59], [58, 61]]}
# gained: {"lines": [22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 34, 35, 36, 37, 40, 49, 50, 51, 52, 53, 54, 55, 58, 59, 61], "branches": [[23, 24], [23, 31], [24, 25], [24, 49], [25, 26], [31, 32], [31, 40], [32, 33], [32, 49], [33, 32], [33, 34], [50, 51], [50, 58], [51, 50], [51, 52], [52, 51], [52, 53], [58, 59], [58, 61]]}

import asyncio
import os
from types import SimpleNamespace
import pytest

from gpt_researcher.document.document import DocumentLoader


class MockPage(SimpleNamespace):
    # SimpleNamespace with expected attributes: page_content and metadata
    pass


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_load_with_list_path(tmp_path):
    # Create two files
    f1 = tmp_path / "file1.txt"
    f1.write_text("hello")
    f2 = tmp_path / "file2.MD"
    f2.write_text("world")

    class LD(DocumentLoader):
        async def _load_document(self, file_path: str, file_extension: str):
            # Return a page with content and metadata.source set to file path
            return [MockPage(page_content=f"content-{file_extension}", metadata={"source": file_path})]

    loader = LD([str(f1), str(f2)])
    docs = asyncio.get_event_loop().run_until_complete(loader.load())

    # Expect two docs corresponding to two files
    assert isinstance(docs, list)
    assert len(docs) == 2
    urls = {d["url"] for d in docs}
    assert urls == {os.path.basename(str(f1)), os.path.basename(str(f2))}
    # Raw content should match the file extension derived in _load_document above
    assert any(d["raw_content"] == "content-txt" for d in docs)
    assert any(d["raw_content"] == "content-md" for d in docs)


def test_load_with_str_path_os_walk(tmp_path):
    # Create directory structure with files in nested dirs
    d1 = tmp_path / "sub"
    d1.mkdir()
    a = tmp_path / "a.TXT"
    a.write_text("a")
    b = d1 / "b.pdf"
    b.write_text("b")
    c = d1 / "c.docx"
    c.write_text("c")

    seen = []

    class LD(DocumentLoader):
        async def _load_document(self, file_path: str, file_extension: str):
            seen.append((file_path, file_extension))
            return [MockPage(page_content=f"ok:{file_extension}", metadata={"source": file_path})]

    loader = LD(str(tmp_path))
    docs = asyncio.get_event_loop().run_until_complete(loader.load())

    # Should have three documents
    assert len(docs) == 3
    # Ensure all basenames are present
    basenames = {d["url"] for d in docs}
    assert basenames == {os.path.basename(str(a)), os.path.basename(str(b)), os.path.basename(str(c))}
    # Ensure extensions recorded in seen (lowercased)
    exts = {ext for _, ext in seen}
    assert exts == {"txt", "pdf", "docx"}


def test_invalid_path_type_raises():
    class LD(DocumentLoader):
        async def _load_document(self, file_path: str, file_extension: str):
            return []

    loader = LD(123)  # invalid type
    with pytest.raises(ValueError, match="Invalid type for path"):
        asyncio.get_event_loop().run_until_complete(loader.load())


def test_no_docs_raises_for_empty_page_content(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("x")

    class LD(DocumentLoader):
        async def _load_document(self, file_path: str, file_extension: str):
            # Return pages with falsy content (empty string)
            return [MockPage(page_content="", metadata={"source": file_path})]

    loader = LD([str(f)])
    with pytest.raises(ValueError, match="Failed to load any documents"):
        asyncio.get_event_loop().run_until_complete(loader.load())
