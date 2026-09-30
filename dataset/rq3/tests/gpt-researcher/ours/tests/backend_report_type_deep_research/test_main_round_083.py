import importlib
import pytest

# Tests exercise backend.report_type.deep_research.main.main
# They patch the GPTResearcher class and write_md_to_pdf symbol where the module resolves them

class DummyProgress:
    def __init__(self, current_depth, total_depth, current_breadth, total_breadth, completed_queries, total_queries, current_query):
        self.current_depth = current_depth
        self.total_depth = total_depth
        self.current_breadth = current_breadth
        self.total_breadth = total_breadth
        self.completed_queries = completed_queries
        self.total_queries = total_queries
        self.current_query = current_query


@pytest.mark.asyncio
async def test_main_progress_no_current_query_round_083(monkeypatch, capsys):
    module = importlib.import_module("backend.report_type.deep_research.main")

    # Fake GPTResearcher that will call the provided on_progress callback with a progress that has no current_query
    class FakeGPTResearcher:
        last_instance = None

        def __init__(self, query=None, report_type=None):
            FakeGPTResearcher.last_instance = self
            self.query = query
            self.report_type = report_type

        async def conduct_research(self, on_progress=None):
            # Call on_progress once with current_query set to None to exercise the branch where no current query is printed
            p = DummyProgress(
                current_depth=1,
                total_depth=3,
                current_breadth=2,
                total_breadth=4,
                completed_queries=0,
                total_queries=5,
                current_query=None,
            )
            # Should match the expected on_progress signature
            if on_progress:
                on_progress(p)
            return {"context": "ok"}

        async def write_report(self):
            return "REPORT_NO_CURRENT"

    written = {}

    async def fake_write_md_to_pdf(report, filename):
        # record call for later assertions
        written['args'] = (report, filename)

    # Patch the symbols where the main module resolves them
    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcher)
    monkeypatch.setattr(module, "write_md_to_pdf", fake_write_md_to_pdf)

    # Run the async main function under test
    await module.main("some task")

    # Capture printed output and assert expected lines
    out = capsys.readouterr().out
    assert "Starting deep research..." in out
    # on_progress prints Depth, Breadth and Queries lines
    assert "Depth: 1/3" in out
    assert "Breadth: 2/4" in out
    assert "Queries: 0/5" in out
    # Because current_query was None, the "Current query:" line should not appear
    assert "Current query:" not in out
    # Final report should be printed
    assert "Final Report: REPORT_NO_CURRENT" in out
    # Ensure write_md_to_pdf was called with the produced report and expected filename
    assert written.get('args') == ("REPORT_NO_CURRENT", "deep_research_report")
    # Ensure the FakeGPTResearcher was constructed with the expected parameters
    inst = FakeGPTResearcher.last_instance
    assert inst is not None
    assert inst.query == "some task"
    assert inst.report_type == "deep"


@pytest.mark.asyncio
async def test_main_progress_with_current_query_round_083(monkeypatch, capsys):
    module = importlib.import_module("backend.report_type.deep_research.main")

    # Fake GPTResearcher variant that provides a current_query value to trigger the other branch
    class FakeGPTResearcherWithQuery:
        last_instance = None

        def __init__(self, query=None, report_type=None):
            FakeGPTResearcherWithQuery.last_instance = self
            self.query = query
            self.report_type = report_type

        async def conduct_research(self, on_progress=None):
            # Provide a progress object with a non-empty current_query
            p = DummyProgress(
                current_depth=2,
                total_depth=4,
                current_breadth=1,
                total_breadth=1,
                completed_queries=3,
                total_queries=3,
                current_query="search-term",
            )
            if on_progress:
                on_progress(p)
            return {"context": "ok2"}

        async def write_report(self):
            return "REPORT_WITH_QUERY"

    recorded = {}

    async def fake_write_md_to_pdf(report, filename):
        recorded['args'] = (report, filename)

    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcherWithQuery)
    monkeypatch.setattr(module, "write_md_to_pdf", fake_write_md_to_pdf)

    await module.main("another task")

    out = capsys.readouterr().out
    assert "Starting deep research..." in out
    # Validate printed progress values
    assert "Depth: 2/4" in out
    assert "Breadth: 1/1" in out
    assert "Queries: 3/3" in out
    # This time the Current query line must appear with the provided string
    assert "Current query: search-term" in out
    # Final report printed
    assert "Final Report: REPORT_WITH_QUERY" in out
    # write_md_to_pdf must be invoked with expected args
    assert recorded.get('args') == ("REPORT_WITH_QUERY", "deep_research_report")
    inst = FakeGPTResearcherWithQuery.last_instance
    assert inst is not None
    assert inst.query == "another task"
    assert inst.report_type == "deep"
