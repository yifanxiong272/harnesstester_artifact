import types
import pytest
from types import SimpleNamespace

from gpt_researcher.document.online_document import OnlineDocumentLoader

@pytest.mark.asyncio
async def test_load_returns_docs_round_077():
    loader = OnlineDocumentLoader(urls=["http://example.com/doc1"])

    async def fake_download_and_process(self, url):
        # single page with content and a source in metadata
        page = SimpleNamespace(page_content="hello world", metadata={"source": url})
        return [page]

    # patch the instance method to avoid any network calls
    loader._download_and_process = types.MethodType(fake_download_and_process, loader)

    docs = await loader.load()

    assert isinstance(docs, list)
    assert docs == [{"raw_content": "hello world", "url": "http://example.com/doc1"}]


@pytest.mark.asyncio
async def test_load_missing_source_round_077():
    loader = OnlineDocumentLoader(urls=["http://no-source.example/"])

    async def fake_download_and_process(self, url):
        # page has content but metadata does not contain 'source'
        page = SimpleNamespace(page_content="content here", metadata={})
        return [page]

    loader._download_and_process = types.MethodType(fake_download_and_process, loader)

    docs = await loader.load()

    # metadata.get("source") should return None and be preserved in the result
    assert docs == [{"raw_content": "content here", "url": None}]


@pytest.mark.asyncio
async def test_load_skip_and_include_round_077():
    loader = OnlineDocumentLoader(urls=["http://example.com/multi"])

    async def fake_download_and_process(self, url):
        # first page empty -> should be skipped; second page has content -> included
        p1 = SimpleNamespace(page_content="", metadata={"source": url + "#1"})
        p2 = SimpleNamespace(page_content="good", metadata={"source": url + "#2"})
        return [p1, p2]

    loader._download_and_process = types.MethodType(fake_download_and_process, loader)

    docs = await loader.load()

    # ensure only the page with truthy page_content was added
    assert len(docs) == 1
    assert docs[0]["raw_content"] == "good"
    assert docs[0]["url"] == "http://example.com/multi#2"


@pytest.mark.asyncio
async def test_load_all_skip_raises_round_077():
    loader = OnlineDocumentLoader(urls=["http://example.com/empty"]) 

    async def fake_download_and_process(self, url):
        # return pages but all have falsy page_content -> should result in no docs
        p1 = SimpleNamespace(page_content=None, metadata={"source": url})
        p2 = SimpleNamespace(page_content="", metadata={"source": url})
        return [p1, p2]

    loader._download_and_process = types.MethodType(fake_download_and_process, loader)

    with pytest.raises(ValueError) as exc:
        await loader.load()

    # verify the error text (the emoji may be present, check main phrase)
    assert "Failed to load any documents" in str(exc.value)
