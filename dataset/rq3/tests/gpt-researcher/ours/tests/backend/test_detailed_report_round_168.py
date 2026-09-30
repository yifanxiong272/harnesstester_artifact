import asyncio
import types
import pytest

import backend.report_type.detailed_report.detailed_report as dr_module


class FakeResearcher:
    """Deterministic fake replacing GPTResearcher used by DetailedReport in tests.

    It preserves the expected constructor signature (accepts kwargs) and provides
    the async methods and attributes the DetailedReport code expects.
    """

    def __init__(self, **kwargs):
        # store params deterministically for assertions if needed
        self.params = kwargs
        # visited_urls and context are simple deterministic containers
        self.visited_urls = set()
        self.context = []
        # cfg with attribute max_search_results_per_query must be writable
        self.cfg = types.SimpleNamespace(max_search_results_per_query=0)

    async def conduct_research(self):
        # deterministically populate context and visited_urls
        self.context = ["ctx-from-fake"]
        self.visited_urls = {"http://fake-research.example/"}

    async def write_introduction(self):
        return "Fake Introduction"


@pytest.mark.asyncio
async def test_run_uses_init_global_urls_round_168(monkeypatch):
    """When _initial_research is a no-op, run() should use the initial global_urls
    (from constructor source_urls) and update the researcher's visited_urls,
    and return the constructed report string.
    """
    # Patch the GPTResearcher symbol where DetailedReport resolves it
    monkeypatch.setattr(dr_module, "GPTResearcher", FakeResearcher)

    # Create a DetailedReport with an initial source_urls value so __init__ sets global_urls
    report = dr_module.DetailedReport(
        query="q",
        report_type="t",
        report_source="s",
        source_urls=["http://init-url.example/"],
    )

    # Make _initial_research a noop so it does not override the constructor-set global_urls
    async def _noop_initial():
        return None

    report._initial_research = _noop_initial

    # Provide deterministic implementations for the other awaited helpers
    async def _get_all_subtopics():
        return [{"id": "sub1"}]

    async def _generate_subtopic_reports(subtopics):
        # simulate returning (ignored, report_body)
        return ("unused", "BODY_FROM_SUBTOPICS")

    async def _construct_detailed_report(intro, body):
        return f"{intro}\n--\n{body}"

    report._get_all_subtopics = _get_all_subtopics
    # Provide a deterministic introduction via the fake researcher as well
    report.gpt_researcher.write_introduction = lambda: asyncio.sleep(0, result="Intro-from-fake")
    report._generate_subtopic_reports = _generate_subtopic_reports
    report._construct_detailed_report = _construct_detailed_report

    # Run and assert return value and that visited_urls got the initial global url
    result = await report.run()

    assert result == "Intro-from-fake\n--\nBODY_FROM_SUBTOPICS"
    # After run(), the fake researcher's visited_urls should include the constructor source URL
    assert "http://init-url.example/" in report.gpt_researcher.visited_urls


@pytest.mark.asyncio
async def test_run_initial_research_updates_global_urls_round_168(monkeypatch):
    """When the researcher's conduct_research populates visited_urls and context,
    run() should pick those up into DetailedReport.global_urls/global_context and
    produce the final report string.
    """
    # Patch GPTResearcher to the deterministic fake
    monkeypatch.setattr(dr_module, "GPTResearcher", FakeResearcher)

    # Instantiate without source_urls so constructor sets empty set
    report = dr_module.DetailedReport(
        query="q2",
        report_type="t2",
        report_source="s2",
        source_urls=[],
    )

    # Do not override _initial_research so it will call the fake researcher's conduct_research
    # Provide deterministic implementations for the other awaited helpers
    async def _get_all_subtopics():
        return []

    async def _generate_subtopic_reports(subtopics):
        return (None, "EMPTY_BODY")

    async def _construct_detailed_report(intro, body):
        return f"INTRO:{intro}|BODY:{body}"

    report._get_all_subtopics = _get_all_subtopics
    report._generate_subtopic_reports = _generate_subtopic_reports
    report._construct_detailed_report = _construct_detailed_report

    # Run and assert the fake researcher's produced context and visited_urls were absorbed,
    # and that the final report is the constructed value.
    result = await report.run()

    assert result == "INTRO:Fake Introduction|BODY:EMPTY_BODY"
    # global_context and global_urls should reflect the fake researcher's values set in conduct_research
    assert report.global_context == ["ctx-from-fake"]
    assert report.global_urls == {"http://fake-research.example/"}
    # The researcher's visited_urls should also contain that url (line where update occurs)
    assert "http://fake-research.example/" in report.gpt_researcher.visited_urls
