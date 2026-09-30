import asyncio
import types
from types import SimpleNamespace
from gpt_researcher.skills.researcher import ResearchConductor


class DummyLogger:
    def __init__(self):
        self.msgs = []

    def info(self, msg):
        # store messages for later inspection
        self.msgs.append(str(msg))


def make_researcher(scraped, context_return, has_vectorstore):
    """
    Create a deterministic fake researcher object with async browse and async context lookup.
    Exposes call-capture lists on created sub-objects for assertions.
    """
    researcher = SimpleNamespace()

    browse_calls = []

    async def browse_urls(urls):
        # record the exact argument list to assert later
        browse_calls.append(list(urls))
        return list(scraped)

    researcher.scraper_manager = SimpleNamespace(browse_urls=browse_urls, _browse_calls=browse_calls)

    get_calls = []

    async def get_similar_content_by_query(query, scraped_content):
        # record query and content, return deterministic context
        get_calls.append((query, list(scraped_content)))
        return context_return

    researcher.context_manager = SimpleNamespace(
        get_similar_content_by_query=get_similar_content_by_query,
        _get_calls=get_calls,
    )

    researcher.query = "test-query"

    if has_vectorstore:
        load_calls = []

        def load(content):
            # vector store loads synchronously in code under test; capture what was passed
            load_calls.append(list(content))

        researcher.vector_store = SimpleNamespace(load=load, _load_calls=load_calls)
    else:
        researcher.vector_store = None

    return researcher


async def _new_urls_impl(self, urls):
    # deterministic transformation used by both tests
    return ["n1", "n2"]


def test_get_context_by_urls_with_vectorstore_round_131():
    # prepare deterministic scraped content and returned context
    scraped = ["doc1", "doc2"]
    context_ret = {"context": "from_vector"}

    researcher = make_researcher(scraped, context_ret, has_vectorstore=True)

    conductor = ResearchConductor(researcher)
    # attach a dummy logger to capture info calls
    conductor.logger = DummyLogger()

    # patch the instance method where the code under test resolves it
    conductor._get_new_urls = types.MethodType(_new_urls_impl, conductor)

    # run the async method deterministically
    result = asyncio.run(conductor._get_context_by_urls(["original-url"]))

    # oracle: returned context should be exactly what the context_manager provided
    assert result == context_ret

    # _get_new_urls should have been called and browse_urls should receive the returned urls
    assert researcher.scraper_manager._browse_calls == [["n1", "n2"]]

    # context_manager should be invoked with researcher.query and the scraped content
    assert researcher.context_manager._get_calls == [(researcher.query, scraped)]

    # when vector_store is present, load should be called with the scraped content
    assert hasattr(researcher.vector_store, "_load_calls")
    assert researcher.vector_store._load_calls == [scraped]

    # logger messages should reflect progression through the function
    # check for presence of messages (string matching rather than exact formatting)
    joined = "\n".join(conductor.logger.msgs)
    assert "Getting context from URLs" in joined
    assert "New URLs to process" in joined
    assert "Scraped content from 2 URLs" in joined


def test_get_context_by_urls_without_vectorstore_round_131():
    # test path where researcher.vector_store is None (branch coverage)
    scraped = ["single-doc"]
    context_ret = ["similar1"]

    researcher = make_researcher(scraped, context_ret, has_vectorstore=False)

    conductor = ResearchConductor(researcher)
    conductor.logger = DummyLogger()
    conductor._get_new_urls = types.MethodType(_new_urls_impl, conductor)

    result = asyncio.run(conductor._get_context_by_urls(["orig2"]))

    # oracle: returned value matches context_manager return
    assert result == context_ret

    # browse called with new urls and context lookup called with the scraped content
    assert researcher.scraper_manager._browse_calls == [["n1", "n2"]]
    assert researcher.context_manager._get_calls == [(researcher.query, scraped)]

    # when no vector_store present, there should be no load calls attribute
    assert researcher.vector_store is None

    # logger should still have recorded the steps
    joined = "\n".join(conductor.logger.msgs)
    assert "Getting context from URLs" in joined
    assert "New URLs to process" in joined
    assert "Scraped content from 1 URLs" in joined
