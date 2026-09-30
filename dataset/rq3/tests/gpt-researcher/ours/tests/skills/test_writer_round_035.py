import asyncio
import json
import types

import pytest

from gpt_researcher.skills import writer


class DummyCfg:
    def __init__(self, agent_role=""):
        self.agent_role = agent_role


class FakeResearcher:
    def __init__(
        self,
        *,
        query="test query",
        cfg=None,
        role="",
        report_type="full_report",
        report_source="src",
        tone="neutral",
        websocket="ws",
        headers=None,
        parent_query="parent",
        verbose=False,
        research_images=None,
        kwargs=None,
    ):
        self.query = query
        self.cfg = cfg or DummyCfg()
        self.role = role
        self.report_type = report_type
        self.report_source = report_source
        self.tone = tone
        self.websocket = websocket
        self.headers = headers or {}
        self.parent_query = parent_query
        self.verbose = verbose
        # function used as cost callback; identity for assertions
        self.add_costs = lambda *a, **k: (a, k)
        # kwargs merged into generate_report call
        self.kwargs = kwargs or {}
        # what get_research_images should return
        self._research_images = research_images
        # fallback context
        self.context = {"ctx": "default"}

    def get_research_images(self):
        return self._research_images


@pytest.mark.asyncio
async def test_write_report_with_images_and_verbose_round_035(monkeypatch):
    """
    - Ensures path where researcher.get_research_images() returns images triggers the initial
      images stream_output call.
    - Ensures available_images + verbose triggers the images_available log stream_output.
    - Ensures verbose triggers writing_report and report_written log stream_output calls.
    - Ensures report_type == 'subtopic_report' causes report_params to include main_topic,
      existing_headers and relevant_written_contents and cost_callback taken from researcher.add_costs.
    """
    calls = []

    async def fake_stream_output(kind, name, payload, websocket, *args, **kwargs):
        # Record the call signature in order for assertions
        calls.append((kind, name, payload, websocket, args, kwargs))

    generated_kwargs = {}

    async def fake_generate_report(**kwargs):
        # capture the kwargs supplied to generate_report for inspection
        generated_kwargs.update(kwargs)
        return "GENERATED_REPORT"

    monkeypatch.setattr(writer, "stream_output", fake_stream_output)
    monkeypatch.setattr(writer, "generate_report", fake_generate_report)

    # Create researcher that will trigger all verbose/image branches
    r = FakeResearcher(
        query="Q",
        cfg=DummyCfg(agent_role=""),  # make agent_role empty so agent_role_prompt is falsy in init
        role="",  # also empty -> causes the inner branch at 97 to run
        report_type="subtopic_report",
        verbose=True,
        research_images=[{"id": 1, "url": "u"}],
        kwargs={"extra_kw": 1},
    )

    gen = writer.ReportGenerator(r)

    # call write_report with some existing headers and relevant contents and with available_images
    report = await gen.write_report(existing_headers=["H1"], relevant_written_contents=["C1"], ext_context={"ctx": "ext"}, custom_prompt="cp", available_images=["imgA"])

    # Return value should be forwarded from fake_generate_report
    assert report == "GENERATED_REPORT"

    # Check stream_output call sequence and key call signatures
    # First call: images selected (json string of research_images)
    assert len(calls) >= 4
    kind0, name0, payload0, ws0, args0, kwargs0 = calls[0]
    assert kind0 == "images"
    assert name0 == "selected_images"
    # payload was json.dumps(research_images)
    assert json.loads(payload0) == r._research_images
    assert ws0 == r.websocket

    # Second call: images_available (because available_images and verbose)
    kind1, name1, payload1, ws1, args1, kwargs1 = calls[1]
    assert kind1 == "logs"
    assert name1 == "images_available"
    assert "pre-generated images available" in payload1
    assert ws1 == r.websocket

    # Third call: writing_report (because verbose)
    kind2, name2, payload2, ws2, args2, kwargs2 = calls[2]
    assert kind2 == "logs"
    assert name2 == "writing_report"
    assert "Writing report for" in payload2
    assert ws2 == r.websocket

    # After generate_report, there should be a report_written log as the last recorded call
    kind_last, name_last, payload_last, ws_last, args_last, kwargs_last = calls[-1]
    assert kind_last == "logs"
    assert name_last == "report_written"
    assert "Report written for" in payload_last
    assert ws_last == r.websocket

    # Validate that generate_report received the expected parameters
    # It should include keys: agent_role_prompt (was falsy originally so branch executed),
    # context (should equal ext_context), custom_prompt, available_images, main_topic, existing_headers,
    # relevant_written_contents, and cost_callback
    assert generated_kwargs.get("context") == {"ctx": "ext"}
    assert generated_kwargs.get("custom_prompt") == "cp"
    assert generated_kwargs.get("available_images") == ["imgA"]
    assert generated_kwargs.get("main_topic") == r.parent_query
    assert generated_kwargs.get("existing_headers") == ["H1"]
    assert generated_kwargs.get("relevant_written_contents") == ["C1"]
    # cost_callback should be the researcher's add_costs callable
    assert generated_kwargs.get("cost_callback") is r.add_costs
    # kwargs from researcher.kwargs must be merged into the final call
    assert generated_kwargs.get("extra_kw") == 1


@pytest.mark.asyncio
async def test_write_report_without_images_non_verbose_round_035(monkeypatch):
    """
    - Ensures path where no research images and non-verbose researcher avoids any stream_output calls.
    - Ensures report_type != 'subtopic_report' uses the else branch setting cost_callback key on report_params.
    - Ensures an initially truthy agent_role_prompt in research_params avoids the fallback assignment branch.
    """
    calls = []

    async def fake_stream_output(*args, **kwargs):
        calls.append((args, kwargs))

    captured = {}

    async def fake_generate_report(**kwargs):
        captured.update(kwargs)
        return "REPORT_NO_IMAGES"

    monkeypatch.setattr(writer, "stream_output", fake_stream_output)
    monkeypatch.setattr(writer, "generate_report", fake_generate_report)

    # Make cfg.agent_role truthy so initial research_params['agent_role_prompt'] is truthy
    r = FakeResearcher(
        query="Q2",
        cfg=DummyCfg(agent_role="agent-x"),
        role="role-fallback",
        report_type="full_report",
        verbose=False,
        research_images=[],
        kwargs={"k": "v"},
    )

    gen = writer.ReportGenerator(r)

    # call without available_images (None) and minimal args
    report = await gen.write_report()

    assert report == "REPORT_NO_IMAGES"

    # Because researcher.get_research_images() returned empty and verbose is False, there should be no stream_output calls
    assert calls == []

    # Ensure the generate_report call included the cost_callback key from the else branch
    assert "cost_callback" in captured
    assert captured["cost_callback"] is r.add_costs

    # Agent role prompt should be preserved from initialization (cfg.agent_role)
    assert captured.get("agent_role_prompt") == "agent-x"

    # Context falls back to researcher.context when ext_context not provided
    assert captured.get("context") == r.context

    # researcher.kwargs merged
    assert captured.get("k") == "v"
