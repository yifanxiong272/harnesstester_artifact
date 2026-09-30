# file: gpt_researcher/skills/writer.py:49-123
# asked: {"lines": [63, 66, 67, 68, 69, 70, 71, 72, 73, 74, 77, 80, 81, 82, 83, 84, 85, 88, 89, 90, 91, 92, 93, 96, 97, 98, 99, 100, 101, 103, 104, 105, 106, 107, 108, 111, 113, 115, 116, 117, 118, 119, 120, 123], "branches": [[67, 68], [67, 77], [80, 81], [80, 88], [88, 89], [88, 96], [97, 98], [97, 99], [103, 104], [103, 111], [115, 116], [115, 123]]}
# gained: {"lines": [63, 66, 67, 68, 69, 70, 71, 72, 73, 74, 77, 80, 81, 82, 83, 84, 85, 88, 89, 90, 91, 92, 93, 96, 97, 98, 99, 100, 101, 103, 104, 105, 106, 107, 108, 111, 113, 115, 116, 117, 118, 119, 120, 123], "branches": [[67, 68], [67, 77], [80, 81], [80, 88], [88, 89], [88, 96], [97, 98], [103, 104], [103, 111], [115, 116], [115, 123]]}

import asyncio
import pytest

from gpt_researcher.skills.writer import ReportGenerator


class DummyCfg:
    def __init__(self, agent_role=""):
        self.agent_role = agent_role


class DummyResearcher:
    def __init__(
        self,
        query="Q",
        cfg=None,
        role="role_default",
        websocket=None,
        verbose=False,
        report_type="full_report",
        parent_query="Parent",
        kwargs=None,
    ):
        self.query = query
        self.cfg = cfg or DummyCfg()
        self.role = role
        self.websocket = websocket
        self.verbose = verbose
        self.report_type = report_type
        self.parent_query = parent_query
        self.report_source = "rsrc"
        self.tone = "neutral"
        self.headers = []
        self.add_costs = lambda *a, **k: ("costs_added", a, k)
        self._research_images = []
        self.kwargs = kwargs or {}
        # Provide a default context so write_report can access researcher.context
        self.context = {"default": "context"}

    def get_research_images(self):
        return self._research_images


def make_async_stub(capture_list, return_value=None):
    async def _stub(*args, **kwargs):
        capture_list.append({"args": args, "kwargs": kwargs})
        return return_value

    return _stub


def make_async_stub_capture_args(capture_list):
    async def _stub(*args, **kwargs):
        capture_list.append((args, kwargs))
        return None

    return _stub


def test_write_report_subtopic_branch(monkeypatch):
    # Prepare researcher with research images and verbose True
    researcher = DummyResearcher(
        query="Test Query",
        cfg=DummyCfg(agent_role="agentX"),
        role="roleY",
        websocket="ws1",
        verbose=True,
        report_type="subtopic_report",
        parent_query="MainTopic",
        kwargs={"extra_kw": "extra_value"},
    )
    researcher._research_images = ["img1", "img2"]

    # Instantiate generator and force agent_role_prompt to be falsy so write_report sets it
    gen = ReportGenerator(researcher)
    gen.research_params["agent_role_prompt"] = ""  # force assignment inside write_report

    # Capture calls
    stream_calls = []
    gen_report_calls = []

    # Patch the generate_report and stream_output used inside the writer module
    monkeypatch.setattr(
        "gpt_researcher.skills.writer.generate_report",
        make_async_stub(gen_report_calls, return_value="GENERATED_REPORT"),
    )
    monkeypatch.setattr(
        "gpt_researcher.skills.writer.stream_output",
        make_async_stub_capture_args(stream_calls),
    )

    # Call write_report
    result = asyncio.run(
        gen.write_report(
            existing_headers=["h1", "h2"],
            relevant_written_contents=["c1"],
            ext_context={"k": "v"},
            custom_prompt="custom",
            available_images=["pre_img"],
        )
    )

    # Assertions about the returned report
    assert result == "GENERATED_REPORT"

    # generate_report should have been called exactly once
    assert len(gen_report_calls) == 1
    gen_call_record = gen_report_calls[0]  # dict with 'args' and 'kwargs'
    gen_kwargs = gen_call_record["kwargs"]
    # verify keys set by write_report
    assert gen_kwargs.get("query") == researcher.query
    # agent_role_prompt should be set to researcher.cfg.agent_role
    assert gen_kwargs.get("agent_role_prompt") == "agentX"
    # context/custom_prompt/available_images set correctly
    assert gen_kwargs.get("context") == {"k": "v"}
    assert gen_kwargs.get("custom_prompt") == "custom"
    assert gen_kwargs.get("available_images") == ["pre_img"]
    # Because report_type is subtopic_report, main_topic and existing_headers and relevant_written_contents should be present
    assert gen_kwargs.get("main_topic") == "MainTopic"
    assert gen_kwargs.get("existing_headers") == ["h1", "h2"]
    assert gen_kwargs.get("relevant_written_contents") == ["c1"]
    # cost_callback should be researcher.add_costs
    assert gen_kwargs.get("cost_callback") == researcher.add_costs
    # Extra kwargs from researcher.kwargs should be present
    assert gen_kwargs.get("extra_kw") == "extra_value"

    # stream_output should have been called 4 times:
    # 1) images, 2) images_available, 3) writing_report, 4) report_written
    assert len(stream_calls) == 4
    # Check first call is images with research_images JSON-ish payload (args capture)
    first_args, _ = stream_calls[0]
    assert first_args[0] == "images"
    assert first_args[1] == "selected_images"
    # the last positional arg should be the research_images list we supplied
    assert list(first_args)[-1] == researcher._research_images

    # Check the images_available log call
    second_args, _ = stream_calls[1]
    assert second_args[0] == "logs"
    assert second_args[1] == "images_available"
    # Check writing_report log call
    third_args, _ = stream_calls[2]
    assert third_args[0] == "logs"
    assert third_args[1] == "writing_report"
    # Check report_written log call
    fourth_args, _ = stream_calls[3]
    assert fourth_args[0] == "logs"
    assert fourth_args[1] == "report_written"


def test_write_report_non_subtopic_no_images_verbose_false(monkeypatch):
    # Prepare researcher without research images and verbose False
    researcher = DummyResearcher(
        query="Another Query",
        cfg=DummyCfg(agent_role=""),  # empty cfg.agent_role to force fallback to role
        role="fallback_role",
        websocket=None,
        verbose=False,
        report_type="full_report",
        kwargs={},
    )
    researcher._research_images = []  # no research images
    # ensure context exists (DummyResearcher provides it)

    gen = ReportGenerator(researcher)
    # Force agent_role_prompt falsy so write_report sets it to cfg.agent_role or role
    gen.research_params["agent_role_prompt"] = ""

    gen_report_calls = []
    stream_calls = []

    monkeypatch.setattr(
        "gpt_researcher.skills.writer.generate_report",
        make_async_stub(gen_report_calls, return_value="REPORT2"),
    )
    monkeypatch.setattr(
        "gpt_researcher.skills.writer.stream_output",
        make_async_stub_capture_args(stream_calls),
    )

    result = asyncio.run(
        gen.write_report(existing_headers=[], relevant_written_contents=[], ext_context=None)
    )

    # verify return value
    assert result == "REPORT2"

    # generate_report should have been called once
    assert len(gen_report_calls) == 1
    gen_kwargs = gen_report_calls[0]["kwargs"]
    # agent_role_prompt should have been set to researcher.role because cfg.agent_role was empty
    assert gen_kwargs.get("agent_role_prompt") == "fallback_role"
    # Since report_type != subtopic_report, main_topic should not be present
    assert "main_topic" not in gen_kwargs
    # cost_callback must still be present
    assert gen_kwargs.get("cost_callback") == researcher.add_costs

    # Because verbose False and no research images, stream_output should not have been called
    assert len(stream_calls) == 0
