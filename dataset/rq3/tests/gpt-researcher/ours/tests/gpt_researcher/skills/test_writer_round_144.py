import asyncio
from types import SimpleNamespace
import gpt_researcher.skills.writer as writer


def test_get_subtopics_verbose_round_144():
    # Arrange: prepare spies and deterministic stubs for async collaborators
    stream_calls = []
    construct_calls = []

    orig_stream = getattr(writer, "stream_output")
    orig_construct = getattr(writer, "construct_subtopics")

    async def fake_stream(kind, tag, message, websocket):
        # record call shape exactly as used by the implementation
        stream_calls.append((kind, tag, message, websocket))
        return None

    async def fake_construct_subtopics(task, data, config, subtopics, prompt_family, **kwargs):
        # record the named parameters and extra kwargs forwarded
        construct_calls.append({
            "task": task,
            "data": data,
            "config": config,
            "subtopics": subtopics,
            "prompt_family": prompt_family,
            "kwargs": kwargs,
        })
        # deterministic returned payload
        return ["subtopic-a", "subtopic-b"]

    # Patch the module-level symbols where the function under test resolves them
    writer.stream_output = fake_stream
    writer.construct_subtopics = fake_construct_subtopics

    try:
        # researcher shape must match what get_subtopics (and ReportGenerator.__init__) expects
        cfg_obj = SimpleNamespace(agent_role=None)
        researcher = SimpleNamespace(
            verbose=True,
            query="test-query",
            websocket="ws://fake",
            context={"ctx": 1},
            cfg=cfg_obj,
            role="researcher-role",
            report_type="summary",
            report_source="source-x",
            tone="neutral",
            headers={"h": 1},
            subtopics=["existing"],
            prompt_family="family-x",
            kwargs={"extra": 42},
        )

        rg = writer.ReportGenerator(researcher)

        # Act: run the async method deterministically
        result = asyncio.run(rg.get_subtopics())

        # Assert: construct_subtopics returned value is propagated
        assert result == ["subtopic-a", "subtopic-b"]

        # construct_subtopics was called exactly once and with expected shapes
        assert len(construct_calls) == 1
        call = construct_calls[0]
        assert call["task"] == "test-query"
        assert call["data"] == {"ctx": 1}
        assert call["config"] == cfg_obj
        assert call["subtopics"] == ["existing"]
        assert call["prompt_family"] == "family-x"
        assert call["kwargs"] == {"extra": 42}

        # Because verbose is True, stream_output must have been awaited twice
        assert len(stream_calls) == 2
        first = stream_calls[0]
        second = stream_calls[1]

        # Verify the first stream call uses the 'generating_subtopics' tag and contains the query
        assert first[0] == "logs"
        assert first[1] == "generating_subtopics"
        assert "test-query" in first[2]
        assert first[3] == "ws://fake"

        # Verify the second stream call uses the 'subtopics_generated' tag and includes the query
        assert second[0] == "logs"
        assert second[1] == "subtopics_generated"
        assert "test-query" in second[2]
        assert second[3] == "ws://fake"

    finally:
        # restore originals to avoid side effects in the test process
        writer.stream_output = orig_stream
        writer.construct_subtopics = orig_construct


def test_get_subtopics_nonverbose_round_144():
    # Arrange: verify behavior when verbose is False (no stream_output calls)
    stream_calls = []
    construct_calls = []

    orig_stream = getattr(writer, "stream_output")
    orig_construct = getattr(writer, "construct_subtopics")

    async def fake_stream(kind, tag, message, websocket):
        stream_calls.append((kind, tag, message, websocket))
        return None

    async def fake_construct_subtopics(task, data, config, subtopics, prompt_family, **kwargs):
        construct_calls.append({
            "task": task,
            "data": data,
            "config": config,
            "subtopics": subtopics,
            "prompt_family": prompt_family,
            "kwargs": kwargs,
        })
        return {"topics": ["only-one"]}

    writer.stream_output = fake_stream
    writer.construct_subtopics = fake_construct_subtopics

    try:
        cfg_obj = SimpleNamespace(agent_role=None)
        researcher = SimpleNamespace(
            verbose=False,
            query="no-stream",
            websocket=None,
            context=None,
            cfg=cfg_obj,
            role="r",
            report_type=None,
            report_source=None,
            tone=None,
            headers=None,
            subtopics=None,
            prompt_family=None,
            kwargs={},
        )

        rg = writer.ReportGenerator(researcher)

        result = asyncio.run(rg.get_subtopics())

        # The returned payload should be exactly the stubbed dict
        assert result == {"topics": ["only-one"]}

        # construct_subtopics was called once with values matching the researcher
        assert len(construct_calls) == 1
        call = construct_calls[0]
        assert call["task"] == "no-stream"
        assert call["data"] is None
        assert call["config"] == cfg_obj
        assert call["subtopics"] is None
        assert call["prompt_family"] is None
        assert call["kwargs"] == {}

        # Because verbose is False, stream_output should not have been awaited
        assert len(stream_calls) == 0

    finally:
        writer.stream_output = orig_stream
        writer.construct_subtopics = orig_construct
