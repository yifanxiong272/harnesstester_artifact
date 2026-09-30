import asyncio
import importlib
from types import SimpleNamespace
import pytest

# Load the module under test
module = importlib.import_module("gpt_researcher.skills.researcher")
ResearchConductor = module.ResearchConductor

# Helper: create a ResearchConductor instance without running its __init__
def make_conductor(researcher_obj, logger_obj=None):
    rc = object.__new__(ResearchConductor)
    rc.researcher = researcher_obj
    if logger_obj is None:
        # simple logger collecting messages
        logs = []
        logger_obj = SimpleNamespace(
            info=lambda msg, *a, **k: logs.append(("info", str(msg))),
            error=lambda msg, *a, **k: logs.append(("error", str(msg)))
        )
        rc._collected_logs = logs
    rc.logger = logger_obj
    return rc

# Async fake stream_output to capture calls deterministically
def make_fake_stream_output(calls_list):
    async def fake_stream_output(channel, event, message, websocket):
        # record a simple tuple for assertions
        calls_list.append((channel, event, str(message), websocket))
    return fake_stream_output

# Retriever classes factories
def retriever_with_results(results):
    class Retriever:
        __name__ = "DummyRetrieverWithResults"
        def __init__(self, query, headers, query_domains, websocket, researcher):
            # store params for possible inspection
            self.query = query
            self.headers = headers
            self.query_domains = query_domains
            self.websocket = websocket
            self.researcher = researcher
        def search(self, max_results=None):
            return list(results)
    return Retriever

def retriever_with_no_results():
    class Retriever:
        __name__ = "DummyRetrieverNoResults"
        def __init__(self, query, headers, query_domains, websocket, researcher):
            self.query = query
            self.headers = headers
            self.query_domains = query_domains
            self.websocket = websocket
            self.researcher = researcher
        def search(self, max_results=None):
            return []
    return Retriever

def retriever_raising_in_init():
    class Retriever:
        __name__ = "DummyRetrieverRaiser"
        def __init__(self, query, headers, query_domains, websocket, researcher):
            raise RuntimeError("init failure")
    return Retriever

@pytest.mark.asyncio
async def test_execute_mcp_research_success_verbose_true_round_039():
    calls = []
    fake = make_fake_stream_output(calls)
    # Patch the module-level stream_output used by the function under test
    module.stream_output = fake

    # Setup researcher object with verbose True
    researcher_obj = SimpleNamespace(
        headers={"h": "v"},
        query_domains=["domain"],
        websocket="ws_obj",
        verbose=True,
        cfg=SimpleNamespace(max_search_results_per_query=5)
    )

    rc = make_conductor(researcher_obj)

    Retriever = retriever_with_results(["r1", "r2"]) 
    result = await ResearchConductor._execute_mcp_research(rc, Retriever, "my query")

    # Return value should be the results
    assert result == ["r1", "r2"]

    # stream_output should have been called twice: stage1 and mcp_research_complete
    events = [c[1] for c in calls]
    assert "mcp_retrieval_stage1" in events
    assert "mcp_research_complete" in events


@pytest.mark.asyncio
async def test_execute_mcp_research_success_verbose_false_round_039():
    calls = []
    fake = make_fake_stream_output(calls)
    module.stream_output = fake

    researcher_obj = SimpleNamespace(
        headers={},
        query_domains=[],
        websocket=None,
        verbose=False,
        cfg=SimpleNamespace(max_search_results_per_query=3)
    )

    rc = make_conductor(researcher_obj)

    Retriever = retriever_with_results(["only"])
    result = await ResearchConductor._execute_mcp_research(rc, Retriever, "query2")

    assert result == ["only"]
    # verbose False -> no stream_output calls
    assert calls == []


@pytest.mark.asyncio
async def test_execute_mcp_research_no_results_verbose_true_round_039():
    calls = []
    fake = make_fake_stream_output(calls)
    module.stream_output = fake

    researcher_obj = SimpleNamespace(
        headers=None,
        query_domains=None,
        websocket="ws",
        verbose=True,
        cfg=SimpleNamespace(max_search_results_per_query=1)
    )

    rc = make_conductor(researcher_obj)

    Retriever = retriever_with_no_results()
    result = await ResearchConductor._execute_mcp_research(rc, Retriever, "noresult query")

    assert result == []
    # When no results and verbose True, stage1 and mcp_no_results should be emitted
    events = [c[1] for c in calls]
    assert "mcp_retrieval_stage1" in events
    assert "mcp_no_results" in events


@pytest.mark.asyncio
async def test_execute_mcp_research_no_results_verbose_false_round_039():
    calls = []
    fake = make_fake_stream_output(calls)
    module.stream_output = fake

    researcher_obj = SimpleNamespace(
        headers=None,
        query_domains=None,
        websocket=None,
        verbose=False,
        cfg=SimpleNamespace(max_search_results_per_query=1)
    )

    rc = make_conductor(researcher_obj)

    Retriever = retriever_with_no_results()
    result = await ResearchConductor._execute_mcp_research(rc, Retriever, "noresult2")

    assert result == []
    # verbose False -> no stream_output calls
    assert calls == []


@pytest.mark.asyncio
async def test_execute_mcp_research_exception_verbose_true_round_039():
    calls = []
    fake = make_fake_stream_output(calls)
    module.stream_output = fake

    researcher_obj = SimpleNamespace(
        headers={},
        query_domains=[],
        websocket="ws_err",
        verbose=True,
        cfg=SimpleNamespace(max_search_results_per_query=2)
    )

    # custom logger to capture error messages
    logged = []
    logger_obj = SimpleNamespace(
        info=lambda msg, *a, **k: logged.append(("info", str(msg))),
        error=lambda msg, *a, **k: logged.append(("error", str(msg)))
    )

    rc = make_conductor(researcher_obj, logger_obj=logger_obj)

    Retriever = retriever_raising_in_init()
    result = await ResearchConductor._execute_mcp_research(rc, Retriever, "bad query")

    # On exception, function returns empty list
    assert result == []
    # Logger should have recorded an error
    assert any(r[0] == "error" for r in logged)
    # verbose True -> stream_output should have been called for the error path
    events = [c[1] for c in calls]
    assert "mcp_research_error" in events


@pytest.mark.asyncio
async def test_execute_mcp_research_exception_verbose_false_round_039():
    calls = []
    fake = make_fake_stream_output(calls)
    module.stream_output = fake

    researcher_obj = SimpleNamespace(
        headers={},
        query_domains=[],
        websocket=None,
        verbose=False,
        cfg=SimpleNamespace(max_search_results_per_query=2)
    )

    logged = []
    logger_obj = SimpleNamespace(
        info=lambda msg, *a, **k: logged.append(("info", str(msg))),
        error=lambda msg, *a, **k: logged.append(("error", str(msg)))
    )

    rc = make_conductor(researcher_obj, logger_obj=logger_obj)

    Retriever = retriever_raising_in_init()
    result = await ResearchConductor._execute_mcp_research(rc, Retriever, "bad2")

    assert result == []
    # verbose False -> no stream_output calls for error
    assert all(ev[1] != "mcp_research_error" for ev in calls)
    # error should still be logged
    assert any(r[0] == "error" for r in logged)
