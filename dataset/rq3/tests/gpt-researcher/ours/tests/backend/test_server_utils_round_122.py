import asyncio
import os
import importlib

import backend.server.server_utils as server_utils


def test_research_round_122():
    """Exercise Researcher.research path with deterministic fakes.

    - Replace CustomLogsHandler with a fake that exposes a deterministic log_file.
    - Replace GPTResearcher with a fake that records calls to its async methods.
    - Replace sanitize_filename and generate_report_files with deterministic stubs.

    Asserts:
    - research() returns expected file paths (pdf/docx/md) from the fake generate_report_files.
    - the returned json path matches the fake logs handler's log_file via os.path.relpath.
    - the fake researcher's async methods were called.
    """

    # Prepare deterministic fakes
    class FakeLogsHandler:
        def __init__(self, websocket, research_id):
            # keep a relative path so os.path.relpath() is stable in tests
            self.log_file = "logs/research.json"

    class FakeGPTResearcher:
        def __init__(self, query, report_type, websocket):
            self.query = query
            self.report_type = report_type
            self.websocket = websocket
            self._conduct_called = False
            self._write_called = False

        async def conduct_research(self):
            # mark called and simulate short async work
            self._conduct_called = True
            return None

        async def write_report(self):
            self._write_called = True
            # return a representative report object (could be string or dict in real code)
            return {"report": "fake content", "query": self.query}

    # Capture arguments passed to generate_report_files for later assertions
    captured = {}

    async def fake_generate_report_files(report, filename):
        captured['report'] = report
        captured['filename'] = filename
        # return deterministic set of file paths
        return {"pdf": "out.pdf", "docx": "out.docx", "md": "out.md"}

    def fake_sanitize_filename(name):
        # deterministic sanitized filename
        return "sanitized_task"

    # Monkeypatch the symbols in the module under test so Researcher will use them
    server_utils.CustomLogsHandler = FakeLogsHandler
    server_utils.GPTResearcher = FakeGPTResearcher
    server_utils.generate_report_files = fake_generate_report_files
    server_utils.sanitize_filename = fake_sanitize_filename

    # Instantiate Researcher; this should exercise __init__ lines (84,85,87,89,90)
    r = server_utils.Researcher("query-for-test", report_type="research_report")

    # Basic sanity about the constructed logs handler
    assert hasattr(r, "logs_handler")
    assert r.logs_handler.log_file == "logs/research.json"

    # Run the async research method and get the result
    result = asyncio.run(r.research())

    # Assertions about behavior exercised during research()
    assert isinstance(result, dict)
    assert "output" in result
    output = result["output"]

    # Check that generate_report_files' returned paths are included
    assert output["pdf"] == "out.pdf"
    assert output["docx"] == "out.docx"
    assert output["md"] == "out.md"

    # The json path should be the relpath of the fake logs handler's log_file
    assert output["json"] == os.path.relpath("logs/research.json")

    # Ensure the GPTResearcher fake had its async methods invoked
    assert getattr(r.researcher, "_conduct_called", False) is True
    assert getattr(r.researcher, "_write_called", False) is True

    # Ensure the generate_report_files fake was called with the report produced by write_report
    assert captured['report'] == {"report": "fake content", "query": "query-for-test"}
    assert captured['filename'] == "sanitized_task"
