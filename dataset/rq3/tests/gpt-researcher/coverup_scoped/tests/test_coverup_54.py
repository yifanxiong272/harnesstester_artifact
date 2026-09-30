# file: gpt_researcher/document/online_document.py:20-34
# asked: {"lines": [21, 22, 23, 24, 25, 26, 27, 28, 31, 32, 34], "branches": [[22, 23], [22, 31], [24, 22], [24, 25], [25, 24], [25, 26], [31, 32], [31, 34]]}
# gained: {"lines": [21, 22, 23, 24, 25, 26, 27, 28, 31, 32, 34], "branches": [[22, 23], [22, 31], [24, 22], [24, 25], [25, 24], [25, 26], [31, 32], [31, 34]]}

import pytest
import asyncio

from gpt_researcher.document.online_document import OnlineDocumentLoader


class _FakePage:
    def __init__(self, content, source):
        self.page_content = content
        self.metadata = {"source": source}


@pytest.mark.asyncio
async def test_load_collects_pages_and_skips_empty(monkeypatch):
    # Arrange: two URLs, some pages have content, one is empty and should be skipped
    urls = ["http://a.example/doc1", "http://b.example/doc2"]
    loader = OnlineDocumentLoader(urls)

    async def fake_download_and_process_first(url):
        # For first URL return two pages: one with content, one empty
        if url == urls[0]:
            return [
                _FakePage("content-1", "http://a.example/doc1"),
                _FakePage("", "http://a.example/doc1#empty"),
            ]
        # For second URL return one page with content
        return [ _FakePage("content-2", "http://b.example/doc2") ]

    # Patch the instance method
    monkeypatch.setattr(loader, "_download_and_process", fake_download_and_process_first)

    # Act
    docs = await loader.load()

    # Assert: only pages with truthy page_content are included, in order
    assert isinstance(docs, list)
    assert len(docs) == 2
    assert docs[0]["raw_content"] == "content-1"
    assert docs[0]["url"] == "http://a.example/doc1"
    assert docs[1]["raw_content"] == "content-2"
    assert docs[1]["url"] == "http://b.example/doc2"


@pytest.mark.asyncio
async def test_load_raises_when_no_documents_loaded(monkeypatch):
    # Arrange: URLs that return only pages without content -> should cause ValueError
    urls = ["http://empty.example/1", "http://empty.example/2"]
    loader = OnlineDocumentLoader(urls)

    async def fake_all_empty(url):
        # return pages with falsy page_content
        return [
            _FakePage("", f"{url}#p1"),
            _FakePage(None, f"{url}#p2"),
        ]

    monkeypatch.setattr(loader, "_download_and_process", fake_all_empty)

    # Act / Assert: ValueError raised with expected message when no docs collected
    with pytest.raises(ValueError) as excinfo:
        await loader.load()

    assert "Failed to load any documents" in str(excinfo.value)
