# file: backend/server/server_utils.py:82-113
# asked: {"lines": [84, 85, 87, 89, 90, 91, 92, 93, 98, 99, 102, 103, 106, 108, 109, 110, 111], "branches": []}
# gained: {"lines": [84, 85, 87, 89, 90, 91, 92, 93, 98, 99, 102, 103, 106, 108, 109, 110, 111], "branches": []}

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
import os
import pytest


def _import_server_utils_module():
    """
    Import the server_utils module as gpt_researcher.backend.server.server_utils by:
    - Locating the server_utils.py file in common repository layouts.
    - Creating minimal dummy modules for external dependencies (fastapi, utils, gpt_researcher.document).
    - Preparing package entries for gpt_researcher and its subpackages so relative imports work.
    Returns the loaded module object.
    """
    # Try normal import first
    try:
        from gpt_researcher.backend.server import server_utils as su  # type: ignore
        return su
    except Exception:
        pass

    # Locate server_utils.py in common locations relative to cwd
    cwd = Path.cwd()
    candidates = [
        cwd / "gpt-researcher" / "backend" / "server" / "server_utils.py",
        cwd / "backend" / "server" / "server_utils.py",
        cwd / "server" / "server_utils.py",
    ]
    server_utils_path = None
    for c in candidates:
        if c.exists():
            server_utils_path = c
            break
    if server_utils_path is None:
        raise FileNotFoundError("Could not find server_utils.py in expected locations")

    # Compute package directories
    # Expect path .../gpt-researcher/backend/server/server_utils.py
    server_dir = server_utils_path.parent
    backend_dir = server_dir.parent
    gpt_pkg_dir = backend_dir.parent

    # Prepare module name
    fullname = "gpt_researcher.backend.server.server_utils"

    # Backup any existing modules we'll override
    backups = {}
    to_create = [
        "gpt_researcher",
        "gpt_researcher.backend",
        "gpt_researcher.backend.server",
        "gpt_researcher.backend.server.multi_agent_runner",
        "gpt_researcher.document.document",
        "utils",
        "fastapi",
        "fastapi.responses",
    ]
    for name in to_create:
        if name in sys.modules:
            backups[name] = sys.modules[name]

    try:
        # Create top-level package module 'gpt_researcher' with a __path__ so relative imports work
        gpt_mod = types.ModuleType("gpt_researcher")
        gpt_mod.__path__ = [str(gpt_pkg_dir)]
        # Provide a placeholder GPTResearcher so "from gpt_researcher import GPTResearcher" succeeds
        class _PlaceholderGPTResearcher:
            def __init__(self, *args, **kwargs):
                pass
        gpt_mod.GPTResearcher = _PlaceholderGPTResearcher
        sys.modules["gpt_researcher"] = gpt_mod

        # Subpackage 'gpt_researcher.backend'
        backend_mod = types.ModuleType("gpt_researcher.backend")
        backend_mod.__path__ = [str(backend_dir)]
        sys.modules["gpt_researcher.backend"] = backend_mod

        # Subpackage 'gpt_researcher.backend.server'
        server_pkg_mod = types.ModuleType("gpt_researcher.backend.server")
        server_pkg_mod.__path__ = [str(server_dir)]
        sys.modules["gpt_researcher.backend.server"] = server_pkg_mod

        # Create a dummy multi_agent_runner module expected by server_utils
        marl = types.ModuleType("gpt_researcher.backend.server.multi_agent_runner")
        def dummy_run_multi_agent_task(*args, **kwargs):
            return {"result": "ok"}
        marl.run_multi_agent_task = dummy_run_multi_agent_task
        sys.modules["gpt_researcher.backend.server.multi_agent_runner"] = marl

        # Provide a dummy document loader module
        docmod = types.ModuleType("gpt_researcher.document.document")
        class DummyDocumentLoader:
            def __init__(self, *args, **kwargs):
                pass
        docmod.DocumentLoader = DummyDocumentLoader
        # Also ensure the parent package exists with __path__ covering gpt_pkg_dir
        doc_pkg = types.ModuleType("gpt_researcher.document")
        doc_pkg.__path__ = [str(gpt_pkg_dir / "document")] if (gpt_pkg_dir / "document").exists() else [str(gpt_pkg_dir)]
        sys.modules["gpt_researcher.document"] = doc_pkg
        sys.modules["gpt_researcher.document.document"] = docmod

        # Provide a minimal 'utils' module used by server_utils
        utils_mod = types.ModuleType("utils")
        def write_md_to_pdf(*args, **kwargs):
            return "/tmp/fake.pdf"
        def write_md_to_word(*args, **kwargs):
            return "/tmp/fake.docx"
        def write_text_to_md(*args, **kwargs):
            return "/tmp/fake.md"
        utils_mod.write_md_to_pdf = write_md_to_pdf
        utils_mod.write_md_to_word = write_md_to_word
        utils_mod.write_text_to_md = write_text_to_md
        sys.modules["utils"] = utils_mod

        # Provide a minimal fastapi and fastapi.responses modules
        fastapi_mod = types.ModuleType("fastapi")
        class DummyHTTPException(Exception):
            pass
        fastapi_mod.HTTPException = DummyHTTPException
        sys.modules["fastapi"] = fastapi_mod

        fr = types.ModuleType("fastapi.responses")
        class JSONResponse:
            def __init__(self, content=None, status_code=200):
                self.content = content
                self.status_code = status_code
        class FileResponse:
            def __init__(self, path, media_type=None, filename=None):
                self.path = path
                self.media_type = media_type
                self.filename = filename
        fr.JSONResponse = JSONResponse
        fr.FileResponse = FileResponse
        sys.modules["fastapi.responses"] = fr

        # Now load the server_utils module under the full package name, so relative imports work
        spec = importlib.util.spec_from_file_location(fullname, str(server_utils_path))
        module = importlib.util.module_from_spec(spec)
        # Insert module into sys.modules under its fullname so relative imports can find it
        sys.modules[fullname] = module
        # Execute the module
        spec.loader.exec_module(module)  # type: ignore

        return module
    finally:
        # Restore any backed-up modules to avoid polluting the test environment
        for name in to_create:
            if name in backups:
                sys.modules[name] = backups[name]
            else:
                # Only remove if we inserted it and it still exists
                if name in sys.modules:
                    del sys.modules[name]


def test_researcher_init_sets_fields(monkeypatch, tmp_path):
    su = _import_server_utils_module()

    # Prepare a fake logs handler which records the provided research_id
    class FakeLogsHandler:
        def __init__(self, *args, **kwargs):
            # create a fake path inside tmp_path to avoid touching real FS
            self.log_file = str(tmp_path / "fake_log.json")
            self.init_args = (args, kwargs)

    # Prepare a fake GPTResearcher that records the websocket passed in
    class FakeGPTResearcher:
        def __init__(self, query, report_type="research_report", websocket=None):
            self.query = query
            self.report_type = report_type
            self.websocket = websocket

        async def conduct_research(self):
            return

        async def write_report(self):
            return "ignored"

    # Patch module-level classes
    monkeypatch.setattr(su, "CustomLogsHandler", FakeLogsHandler, raising=False)
    monkeypatch.setattr(su, "GPTResearcher", FakeGPTResearcher, raising=False)

    # Now instantiate Researcher and verify fields
    r = su.Researcher("example query", report_type="research_report")

    # research_id should be a string and not contain the raw query
    assert isinstance(r.research_id, str)
    assert "example query" not in r.research_id

    # logs_handler should be our FakeLogsHandler and researcher should be FakeGPTResearcher
    assert isinstance(r.logs_handler, FakeLogsHandler)
    assert isinstance(r.researcher, FakeGPTResearcher)

    # The websocket passed into GPTResearcher should be the same logs handler instance
    assert r.researcher.websocket is r.logs_handler

    # report_type and query attributes should be preserved
    assert r.query == "example query"
    assert r.report_type == "research_report"


def test_researcher_research_executes_all_steps(monkeypatch, tmp_path):
    su = _import_server_utils_module()

    called = {}

    # Fake logs handler; set log_file to a path inside tmp_path
    class FakeLogsHandler:
        def __init__(self, *args, **kwargs):
            log_path = tmp_path / "logs"
            log_path.mkdir(parents=True, exist_ok=True)
            self.log_file = str(log_path / "some_log.json")

    # Fake GPTResearcher that records that its async methods were called and returns a report
    class FakeGPTResearcher:
        def __init__(self, query, report_type="research_report", websocket=None):
            self.query = query
            self.report_type = report_type
            self.websocket = websocket

        async def conduct_research(self):
            called["conduct_research"] = True

        async def write_report(self):
            called["write_report"] = True
            return {"title": "Fake Report", "content": "This is a test."}

    # Async fake generate_report_files
    async def fake_generate_report_files(report, sanitized_filename):
        called["generate_report_files_args"] = (report, sanitized_filename)
        return {
            "pdf": f"{sanitized_filename}.pdf",
            "docx": f"{sanitized_filename}.docx",
            "md": f"{sanitized_filename}.md",
        }

    # Fake sanitize_filename that returns a predictable name and records input
    def fake_sanitize_filename(name):
        called["sanitize_filename_arg"] = name
        return "sanitized_task_name"

    # Patch the module-level dependencies
    monkeypatch.setattr(su, "CustomLogsHandler", FakeLogsHandler, raising=False)
    monkeypatch.setattr(su, "GPTResearcher", FakeGPTResearcher, raising=False)
    monkeypatch.setattr(su, "generate_report_files", fake_generate_report_files, raising=False)
    monkeypatch.setattr(su, "sanitize_filename", fake_sanitize_filename, raising=False)

    # Instantiate Researcher
    r = su.Researcher("some query for files", report_type="detailed_report")

    # Run the async research method
    result = asyncio.run(r.research())

    # Assert that the GPTResearcher methods were called
    assert called.get("conduct_research", False) is True
    assert called.get("write_report", False) is True

    # sanitize_filename should have been called with a name that starts with "task_"
    sf_arg = called.get("sanitize_filename_arg")
    assert sf_arg is not None
    assert sf_arg.startswith("task_"), f"sanitize_filename called with unexpected arg: {sf_arg}"

    # generate_report_files should have been called with the report returned by write_report
    gen_args = called.get("generate_report_files_args")
    assert gen_args is not None
    report_passed, sanitized_passed = gen_args
    assert isinstance(report_passed, dict) and report_passed.get("title") == "Fake Report"
    assert sanitized_passed == "sanitized_task_name"

    # The returned structure should include pdf/docx/md from our fake generator and json relative path
    assert "output" in result
    out = result["output"]
    assert out["pdf"] == "sanitized_task_name.pdf"
    assert out["docx"] == "sanitized_task_name.docx"
    assert out["md"] == "sanitized_task_name.md"

    # json should be the relpath of the logs_handler.log_file (relative to current working dir)
    expected_json_rel = os.path.relpath(r.logs_handler.log_file)
    assert out["json"] == expected_json_rel
