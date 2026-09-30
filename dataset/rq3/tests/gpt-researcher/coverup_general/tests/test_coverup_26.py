# file: backend/report_type/detailed_report/detailed_report.py:138-195
# asked: {"lines": [139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 156, 157, 161, 162, 164, 165, 167, 169, 170, 172, 173, 174, 176, 177, 181, 182, 183, 186, 187, 188, 190, 191, 192, 195], "branches": [[161, 162], [161, 164], [169, 170], [169, 172]]}
# gained: {"lines": [139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 156, 157, 161, 162, 164, 165, 167, 169, 170, 172, 173, 174, 176, 177, 181, 182, 183, 186, 187, 188, 190, 191, 192, 195], "branches": [[161, 162], [161, 164], [169, 170], [169, 172]]}

import sys
import importlib.util
from types import ModuleType
from pathlib import Path
import pytest


def _load_detailed_report_module():
    # Search for the detailed_report.py file in the repository tree (cwd first)
    cwd = Path.cwd()
    candidates = list(cwd.rglob("detailed_report.py"))
    # Also try relative to this file if running from different CWD
    this_file = Path(__file__).resolve()
    candidates += list(this_file.parent.rglob("detailed_report.py"))
    # Filter to ones likely in report_type/detailed_report directory
    candidates = [p for p in candidates if "report_type" in p.parts]
    if not candidates:
        raise ImportError("Could not find detailed_report.py in repository tree.")
    target = candidates[0]

    # Provide a temporary fake 'gpt_researcher' module so top-level import doesn't fail
    orig = sys.modules.get("gpt_researcher")
    fake = ModuleType("gpt_researcher")
    fake.GPTResearcher = None  # placeholder; will be monkeypatched in tests
    sys.modules["gpt_researcher"] = fake
    try:
        spec = importlib.util.spec_from_file_location("gpt_researcher.backend.report_type.detailed_report.detailed_report", str(target))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)  # type: ignore
    finally:
        # restore original if any
        if orig is not None:
            sys.modules["gpt_researcher"] = orig
        else:
            del sys.modules["gpt_researcher"]
    return module


module = _load_detailed_report_module()
DetailedReport = module.DetailedReport


class DummyParentResearcher:
    def __init__(self):
        self.agent = "agent-x"
        self.role = "role-x"
        self.mcp_configs = {"cfg": 1}
        self.mcp_strategy = "strategy-x"

    def extract_headers(self, data):
        # Always return list of dicts with 'text' key (used by code under test)
        if isinstance(data, list):
            return [{"text": str(v)} for v in data]
        return [{"text": str(data)}]

    def extract_sections(self, report_text):
        return [f"section-from-{report_text}"]


@pytest.mark.asyncio
async def test_get_subtopic_report_with_max_search_results_and_nonstring_draft_titles(monkeypatch):
    created_instances = []

    class FakeCFG:
        def __init__(self):
            self.max_search_results_per_query = None

    class FakeGPTResearcher:
        def __init__(self, *args, **kwargs):
            created_instances.append(self)
            self.cfg = FakeCFG()
            self.context = []
            self.visited_urls = set()
            self._init_kwargs = kwargs

        async def conduct_research(self):
            # simulate adding new context and marking visited urls
            self.context = list(set(self.context + ["new_context"]))
            self.visited_urls.update({"http://example.com/subtopic"})

        async def get_draft_section_titles(self, current_subtopic_task):
            # return a non-string to trigger conversion branch
            return ["Draft Title 1", "Draft Title 2"]

        async def get_similar_written_contents_by_draft_section_titles(self, current_subtopic_task, titles, global_written_sections):
            return [{"sim": "content"}]

        async def write_report(self, existing_headers, relevant_written_contents):
            return "SUBTOPIC REPORT"

    # Patch the module-level GPTResearcher to our fake class
    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcher)

    fake_self = type("FS", (), {})()
    fake_self.query_domains = ["domain"]
    fake_self.report_source = "rsrc"
    fake_self.websocket = None
    fake_self.headers = {"H": "v"}
    fake_self.query = "parent query"
    fake_self.subtopics = []
    fake_self.global_urls = set()
    fake_self.gpt_researcher = DummyParentResearcher()
    fake_self.tone = "neutral"
    fake_self.complement_source_urls = []
    fake_self.source_urls = []
    fake_self.max_search_results = "4"  # non-None to exercise cfg assignment branch
    fake_self.existing_headers = []
    fake_self.global_written_sections = []
    fake_self.global_context = ["initial_ctx"]
    fake_self._hashable_context = lambda ctx: [str(c) for c in ctx]

    subtopic = {"task": "do something"}

    result = await DetailedReport._get_subtopic_report(fake_self, subtopic)

    assert isinstance(result, dict)
    assert result["topic"] == subtopic
    assert result["report"] == "SUBTOPIC REPORT"

    assert len(created_instances) >= 1
    inst = created_instances[-1]
    assert inst.cfg.max_search_results_per_query == int(fake_self.max_search_results)

    assert fake_self.existing_headers, "existing_headers should not be empty"
    last_header = fake_self.existing_headers[-1]
    assert last_header["subtopic task"] == subtopic.get("task")
    assert isinstance(last_header["headers"], list)
    assert "text" in last_header["headers"][0]

    assert fake_self.global_written_sections == fake_self.gpt_researcher.extract_sections("SUBTOPIC REPORT")

    # global_context should include new_context
    assert "new_context" in fake_self.global_context

    # global_urls should include visited url from fake researcher
    assert "http://example.com/subtopic" in fake_self.global_urls


@pytest.mark.asyncio
async def test_get_subtopic_report_without_max_search_results_and_string_draft_titles(monkeypatch):
    created_instances = []

    class FakeCFG:
        def __init__(self):
            self.max_search_results_per_query = None

    class FakeGPTResearcherStrTitle:
        def __init__(self, *args, **kwargs):
            created_instances.append(self)
            self.cfg = FakeCFG()
            self.context = []
            self.visited_urls = set()
            self._init_kwargs = kwargs

        async def conduct_research(self):
            # do not change context for this variant
            self.context = list(set(self.context))

        async def get_draft_section_titles(self, current_subtopic_task):
            # return a string to exercise the string branch
            return "A single draft title string"

        async def get_similar_written_contents_by_draft_section_titles(self, current_subtopic_task, titles, global_written_sections):
            return []

        async def write_report(self, existing_headers, relevant_written_contents):
            return "REPORT-STR-TITLE"

    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcherStrTitle)

    fake_self = type("FS", (), {})()
    fake_self.query_domains = []
    fake_self.report_source = None
    fake_self.websocket = None
    fake_self.headers = {}
    fake_self.query = "parent query 2"
    fake_self.subtopics = []
    fake_self.global_urls = set()
    fake_self.gpt_researcher = DummyParentResearcher()
    fake_self.tone = "formal"
    fake_self.complement_source_urls = []
    fake_self.source_urls = []
    fake_self.max_search_results = None  # None -> branch not taken
    fake_self.existing_headers = []
    fake_self.global_written_sections = ["existing_section"]
    fake_self.global_context = []
    fake_self._hashable_context = lambda ctx: [str(c) for c in ctx]

    subtopic = {"task": "another task"}

    result = await DetailedReport._get_subtopic_report(fake_self, subtopic)

    assert result["topic"] == subtopic
    assert result["report"] == "REPORT-STR-TITLE"

    assert len(created_instances) >= 1
    inst = created_instances[-1]
    assert inst.cfg.max_search_results_per_query is None

    assert any("REPORT-STR-TITLE" in s for s in fake_self.global_written_sections)

    assert fake_self.existing_headers
    last_header = fake_self.existing_headers[-1]
    assert last_header["subtopic task"] == "another task"
    assert isinstance(last_header["headers"], list)
    assert "text" in last_header["headers"][0]
