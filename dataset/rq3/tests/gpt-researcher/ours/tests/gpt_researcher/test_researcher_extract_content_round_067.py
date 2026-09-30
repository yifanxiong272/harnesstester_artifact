import asyncio
import pytest
from types import SimpleNamespace
from gpt_researcher.skills.researcher import ResearchConductor


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg):
        # keep deterministic capture of messages
        self.messages.append(str(msg))


@pytest.mark.asyncio
async def test_no_results_round_067():
    """
    When results is empty, _extract_content should log and return an empty list.
    Covers: branch where urls list is empty -> early return [].
    """
    rc = ResearchConductor.__new__(ResearchConductor)
    rc.logger = DummyLogger()
    # researcher with minimal expected attributes
    rc.researcher = SimpleNamespace(visited_urls=set(), scraper_manager=SimpleNamespace())

    result = await ResearchConductor._extract_content(rc, [])

    assert result == []
    assert len(rc.logger.messages) == 1
    assert "Extracting content from 0 search results" in rc.logger.messages[0]


@pytest.mark.asyncio
async def test_non_dict_results_round_067():
    """
    If results contain non-dict items, they should be ignored and empty urls lead to [] return.
    Covers loop branch where isinstance(result, dict) is False.
    """
    rc = ResearchConductor.__new__(ResearchConductor)
    rc.logger = DummyLogger()
    rc.researcher = SimpleNamespace(visited_urls=set(), scraper_manager=SimpleNamespace())

    results = ["just a string", 123, [1, 2, 3]]
    returned = await ResearchConductor._extract_content(rc, results)

    assert returned == []
    assert "Extracting content from 3 search results" in rc.logger.messages[0]


@pytest.mark.asyncio
async def test_all_urls_already_visited_round_067():
    """
    When all found urls are already in visited_urls, method should return [].
    Covers branch checking new_urls and returning empty when none new.
    """
    rc = ResearchConductor.__new__(ResearchConductor)
    rc.logger = DummyLogger()
    # prepare visited urls to include all expected hrefs
    visited = {"https://a.example", "https://b.example"}
    rc.researcher = SimpleNamespace(visited_urls=visited, scraper_manager=SimpleNamespace())

    results = [{"href": "https://a.example"}, {"href": "https://b.example"}]
    returned = await ResearchConductor._extract_content(rc, results)

    assert returned == []
    # visited_urls should remain unchanged
    assert rc.researcher.visited_urls == {"https://a.example", "https://b.example"}


@pytest.mark.asyncio
async def test_scrape_and_update_visited_round_067():
    """
    When new urls are present, browse_urls should be awaited, its return value returned,
    and visited_urls updated with the new urls.
    Covers branch where scrape is invoked and visited_urls.update is executed.
    """
    rc = ResearchConductor.__new__(ResearchConductor)
    rc.logger = DummyLogger()

    # Start with one visited URL to ensure filtering of new vs existing
    visited = {"https://seen.example"}

    called_args = []

    async def fake_browse(urls):
        # record the exact argument for later assertions and return deterministic content
        called_args.append(list(urls))
        return [f"scraped:{u}" for u in urls]

    rc.researcher = SimpleNamespace(visited_urls=visited, scraper_manager=SimpleNamespace(browse_urls=fake_browse))

    results = [
        {"href": "https://seen.example"},  # already visited -> filtered out
        {"href": "https://new.example"},
        {"not_href": "ignored"},  # should be ignored by isinstance+"href" check
    ]

    returned = await ResearchConductor._extract_content(rc, results)

    # browse_urls should have been called exactly once with only the new url
    assert called_args == [["https://new.example"]]

    # returned scraped content should match fake_browse output
    assert returned == ["scraped:https://new.example"]

    # visited_urls should be updated to include the new url
    assert "https://new.example" in rc.researcher.visited_urls
    assert "https://seen.example" in rc.researcher.visited_urls
