# file: gpt_researcher/skills/researcher.py:233-264
# asked: {"lines": [239, 240, 242, 244, 245, 247, 248, 249, 250, 251, 252, 253, 254, 258, 259, 260, 261, 264], "branches": [[244, 245], [244, 247], [247, 248], [247, 258]]}
# gained: {"lines": [239, 240, 242, 244, 245, 247, 248, 249, 250, 251, 252, 253, 254, 258, 259, 260, 261, 264], "branches": [[244, 245], [244, 247], [247, 248], [247, 258]]}

import asyncio
import types
import pytest

# Attempt to import the ResearchConductor class from the expected module path.
# The repository layout provided indicates the module path: gpt_researcher.skills.researcher
from gpt_researcher.skills.researcher import ResearchConductor


def make_simple_logger(captured):
    class Logger:
        def info(self, msg):
            captured.append(msg)
    return Logger()


def make_researcher(report_type="full_report", verbose=True, websocket="ws"):
    r = types.SimpleNamespace()
    r.report_type = report_type
    r.verbose = verbose
    r.websocket = websocket
    return r


def _mk_async(func):
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def test_get_context_appends_query_and_calls_stream_output(monkeypatch):
    """
    - plan_research returns two subqueries
    - researcher.report_type != "subtopic_report" so original query is appended
    - researcher.verbose is True so stream_output should be called with expected args
    - _process_sub_query_with_vectorstore should be awaited for each subquery and return expected results
    """
    # Create instance without running __init__
    rc = object.__new__(ResearchConductor)

    # Capture logger messages
    log_msgs = []
    rc.logger = make_simple_logger(log_msgs)

    # plan_research: async function returning two subqueries
    async def fake_plan_research(query):
        assert query == "original query"
        return ["sub1", "sub2"]

    rc.plan_research = fake_plan_research

    # researcher attributes: not a subtopic_report, verbose True
    rc.researcher = make_researcher(report_type="full_report", verbose=True, websocket="fake_ws")

    # Prepare to capture calls to stream_output in the module where ResearchConductor is defined.
    # The method under test imports stream_output into its module namespace; monkeypatch that name.
    called_stream = {}

    async def fake_stream_output(channel, name, message, websocket, boolean_flag, sub_queries):
        # record call
        called_stream['args'] = (channel, name, message, websocket, boolean_flag, list(sub_queries))
        # emulate sending messages by returning something
        return {"sent": True}

    # Patch stream_output in the ResearchConductor module
    import importlib
    mod = importlib.import_module(ResearchConductor.__module__)
    monkeypatch.setattr(mod, "stream_output", fake_stream_output)

    # _process_sub_query_with_vectorstore: async function that returns processed results
    async def fake_process(sub_query, filter):
        # return an identifiable result per subquery
        return f"processed:{sub_query}:{filter}"

    rc._process_sub_query_with_vectorstore = fake_process

    # Call the coroutine
    result = asyncio.run(rc._get_context_by_vectorstore("original query", filter={"k": "v"}))

    # Assertions: logger was used
    assert any("Starting vectorstore search for query: original query" in m for m in log_msgs)

    # plan_research returned two then original appended => 3 items processed
    assert result == [
        "processed:sub1:{'k': 'v'}",
        "processed:sub2:{'k': 'v'}",
        "processed:original query:{'k': 'v'}",
    ]

    # stream_output must have been called and the message should include the subqueries list
    assert 'args' in called_stream
    channel, name, message, websocket, boolean_flag, subqueries_passed = called_stream['args']
    assert channel == "logs"
    assert name == "subqueries"
    assert "🗂️" in message or "subqueries" in message  # message includes subqueries description
    assert websocket == "fake_ws"
    assert boolean_flag is True
    # subqueries_passed should be the list used (sub1, sub2, original query)
    assert subqueries_passed == ["sub1", "sub2", "original query"]


def test_get_context_no_append_and_no_stream_when_subtopic_report(monkeypatch):
    """
    - plan_research returns one subquery
    - researcher.report_type == "subtopic_report" so original query is NOT appended
    - researcher.verbose is False so stream_output should NOT be called
    - ensure filter is forwarded to processing function
    """
    rc = object.__new__(ResearchConductor)

    log_msgs = []
    rc.logger = make_simple_logger(log_msgs)

    async def fake_plan_research(query):
        assert query == "q2"
        return ["onlysub"]

    rc.plan_research = fake_plan_research

    # researcher attributes: subtopic_report and not verbose
    rc.researcher = make_researcher(report_type="subtopic_report", verbose=False, websocket=None)

    # Replace stream_output with a function that fails the test if called
    import importlib
    mod = importlib.import_module(ResearchConductor.__module__)

    async def failing_stream_output(*args, **kwargs):
        pytest.fail("stream_output should not be called when researcher.verbose is False")

    monkeypatch.setattr(mod, "stream_output", failing_stream_output)

    # _process_sub_query_with_vectorstore should receive the filter and return a result
    received = {}

    async def fake_process(sub_query, filter):
        received['sub_query'] = sub_query
        received['filter'] = filter
        return f"done:{sub_query}"

    rc._process_sub_query_with_vectorstore = fake_process

    # Call and assert
    filt = {"a": 1}
    result = asyncio.run(rc._get_context_by_vectorstore("q2", filter=filt))

    # Only the single returned processing result should be present (no appended original query)
    assert result == ["done:onlysub"]
    # Ensure the filter was forwarded unchanged
    assert received['filter'] is filt
    assert received['sub_query'] == "onlysub"
    # Ensure the starting log message was produced
    assert any("Starting vectorstore search for query: q2" in m for m in log_msgs)
