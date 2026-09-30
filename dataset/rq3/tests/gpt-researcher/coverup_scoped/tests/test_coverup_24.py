# file: backend/report_type/detailed_report/detailed_report.py:138-195
# asked: {"lines": [139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 156, 157, 161, 162, 164, 165, 167, 169, 170, 172, 173, 174, 176, 177, 181, 182, 183, 186, 187, 188, 190, 191, 192, 195], "branches": [[161, 162], [161, 164], [169, 170], [169, 172]]}
# gained: {"lines": [139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 156, 157, 161, 162, 164, 165, 167, 169, 170, 172, 173, 174, 176, 177, 181, 182, 183, 186, 187, 188, 190, 191, 192, 195], "branches": [[161, 162], [169, 170]]}

import importlib.util
import os
from pathlib import Path
import pytest
from types import SimpleNamespace

pytest_plugins = ("pytest_asyncio",)


def _locate_detailed_report_file():
    # Search repository for a file named detailed_report.py that defines DetailedReport
    repo_root = Path.cwd()
    for path in repo_root.rglob("detailed_report.py"):
        try:
            text = path.read_text(encoding="utf8")
        except Exception:
            continue
        if "class DetailedReport" in text and "async def _get_subtopic_report" in text:
            return path
    raise FileNotFoundError("Could not find detailed_report.py containing DetailedReport")


def _load_module_from_path(path: Path, module_name: str = "tested_detailed_report"):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise ImportError(f"Could not load spec for {path}")
    loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_get_subtopic_report_executes_all_branches_and_updates_state(monkeypatch):
    # Locate and load the actual module file to ensure we execute original code lines.
    path = _locate_detailed_report_file()
    module = _load_module_from_path(path, module_name="tested_detailed_report_module")
    DetailedReport = getattr(module, "DetailedReport")

    # Create a fake GPTResearcher to replace the real one inside the loaded module.
    class FakeGPTResearcher:
        instances = []

        def __init__(self, *args, **kwargs):
            self.init_args = args
            self.init_kwargs = kwargs
            self.query = kwargs.get("query")
            # Attributes expected by DetailedReport logic
            self.agent = kwargs.get("agent", "fake-agent")
            self.role = kwargs.get("role", "fake-role")
            self.mcp_configs = kwargs.get("mcp_configs", {"mc": 1})
            self.mcp_strategy = kwargs.get("mcp_strategy", "fake-strategy")
            self.cfg = SimpleNamespace(max_search_results_per_query=None)
            self.context = ["initial-context"]
            self.visited_urls = set()
            FakeGPTResearcher.instances.append(self)

        async def conduct_research(self):
            # Simulate research effects
            self.context = ["ctx1", "ctx2"]
            self.visited_urls = {"http://example.com", "http://other.com"}

        async def get_draft_section_titles(self, task):
            # Return a non-string to hit the branch that converts it to str
            return ["Draft Section A", "Draft Section B"]

        async def get_similar_written_contents_by_draft_section_titles(self, task, titles, global_written_sections):
            return ["similar content 1"]

        async def write_report(self, existing_headers=None, relevant_written_contents=None):
            return f"REPORT for: {self.query}"

        # Methods expected on the parent gpt_researcher (DetailedReport.gpt_researcher)
        def extract_headers(self, text):
            return [{"text": "Header 1"}, {"text": "Header 2"}]

        def extract_sections(self, text):
            return [f"section from {text}"]

    # Patch the module's GPTResearcher symbol before creating DetailedReport instance
    monkeypatch.setattr(module, "GPTResearcher", FakeGPTResearcher)

    # Ensure no leftover instances
    FakeGPTResearcher.instances.clear()

    # Create DetailedReport instance with parameters to trigger branches (including max_search_results)
    dr = DetailedReport(
        query="Parent Query",
        report_type="detailed_report",
        report_source="test_source",
        source_urls=[],
        query_domains=["domain1"],
        tone="neutral",
        headers={"some": "header"},
        complement_source_urls=False,
        mcp_configs={"mc": 1},
        mcp_strategy="strategy-x",
        max_search_results=3,
    )

    # Prepare subtopic and call the async method
    subtopic = {"task": "Write about testing"}
    result = await dr._get_subtopic_report(subtopic)

    # Assertions verifying returned structure and state updates
    assert isinstance(result, dict)
    assert result["topic"] is subtopic
    assert result["report"] == "REPORT for: Write about testing"

    # There should be at least two FakeGPTResearcher instances:
    # first is the parent gpt_researcher, last is the subtopic assistant
    assert len(FakeGPTResearcher.instances) >= 2
    parent_instance = FakeGPTResearcher.instances[0]
    subtopic_instance = FakeGPTResearcher.instances[-1]

    # MCP configs and strategy propagated to subtopic assistant via init kwargs
    assert subtopic_instance.init_kwargs.get("mcp_configs") == parent_instance.mcp_configs
    assert subtopic_instance.init_kwargs.get("mcp_strategy") == parent_instance.mcp_strategy

    # max_search_results override applied to the subtopic assistant's cfg
    assert subtopic_instance.cfg.max_search_results_per_query == int(3)

    # global_context updated from subtopic_assistant.context
    assert set(dr.global_context) == set(["ctx1", "ctx2"])

    # global_written_sections extended using extract_sections on the subtopic report
    assert dr.global_written_sections == [f"section from REPORT for: Write about testing"]

    # global_urls should include visited URLs from subtopic assistant
    assert "http://example.com" in dr.global_urls and "http://other.com" in dr.global_urls

    # existing_headers should contain an entry for this subtopic with extracted headers
    assert dr.existing_headers, "existing_headers should not be empty"
    last_header_entry = dr.existing_headers[-1]
    assert last_header_entry["subtopic task"] == "Write about testing"
    assert last_header_entry["headers"] == [{"text": "Header 1"}, {"text": "Header 2"}]

    # Cleanup
    FakeGPTResearcher.instances.clear()
