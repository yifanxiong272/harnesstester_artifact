# file: backend/server/server_utils.py:126-178
# asked: {"lines": [127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145, 148, 150, 151, 152, 153, 154, 157, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 174, 175, 177, 178], "branches": [[143, 144], [143, 148]]}
# gained: {"lines": [127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 143, 144, 145, 148, 150, 151, 152, 153, 154, 157, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 174, 175, 177, 178], "branches": [[143, 144], [143, 148]]}

import asyncio
import json
import os
import importlib.util
import sys
import types
from pathlib import Path
import pytest

def load_server_utils_module():
    # Locate the server_utils.py relative to this test file
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "gpt-researcher" / "backend" / "server" / "server_utils.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Could not find server_utils.py at {module_path}")

    # Prepare stub modules to satisfy imports that would otherwise fail due to package context
    added_modules = {}
    def add_module(name, module_obj):
        added_modules[name] = sys.modules.get(name)
        sys.modules[name] = module_obj

    # Minimal stubs for gpt_researcher package and submodules
    gpt_pkg = types.ModuleType("gpt_researcher")
    setattr(gpt_pkg, "GPTResearcher", type("GPTResearcher", (), {}))
    add_module("gpt_researcher", gpt_pkg)

    gpt_doc_pkg = types.ModuleType("gpt_researcher.document")
    add_module("gpt_researcher.document", gpt_doc_pkg)

    gpt_doc_doc = types.ModuleType("gpt_researcher.document.document")
    setattr(gpt_doc_doc, "DocumentLoader", type("DocumentLoader", (), {}))
    add_module("gpt_researcher.document.document", gpt_doc_doc)

    # Backend packages
    backend_pkg = types.ModuleType("gpt_researcher.backend")
    add_module("gpt_researcher.backend", backend_pkg)
    backend_server_pkg = types.ModuleType("gpt_researcher.backend.server")
    add_module("gpt_researcher.backend.server", backend_server_pkg)

    # Stub for multi_agent_runner relative import
    multi_agent_runner = types.ModuleType("gpt_researcher.backend.server.multi_agent_runner")
    def run_multi_agent_task(*args, **kwargs):
        return None
    setattr(multi_agent_runner, "run_multi_agent_task", run_multi_agent_task)
    add_module("gpt_researcher.backend.server.multi_agent_runner", multi_agent_runner)

    # utils module used by server_utils
    utils_mod = types.ModuleType("utils")
    setattr(utils_mod, "write_md_to_pdf", lambda *a, **k: None)
    setattr(utils_mod, "write_md_to_word", lambda *a, **k: None)
    setattr(utils_mod, "write_text_to_md", lambda *a, **k: None)
    add_module("utils", utils_mod)

    # fastapi stubs
    fastapi_mod = types.ModuleType("fastapi")
    setattr(fastapi_mod, "HTTPException", Exception)
    add_module("fastapi", fastapi_mod)
    fastapi_resp = types.ModuleType("fastapi.responses")
    class JSONResponse:
        def __init__(self, *a, **k): pass
    class FileResponse:
        def __init__(self, *a, **k): pass
    setattr(fastapi_resp, "JSONResponse", JSONResponse)
    setattr(fastapi_resp, "FileResponse", FileResponse)
    add_module("fastapi.responses", fastapi_resp)

    # Now load the module
    spec = importlib.util.spec_from_file_location("gpt_researcher.backend.server.server_utils", str(module_path))
    module = importlib.util.module_from_spec(spec)
    # Ensure proper package context
    module.__package__ = "gpt_researcher.backend.server"
    try:
        spec.loader.exec_module(module)
    finally:
        # Clean up the temporary stub modules to avoid polluting other tests
        for name, previous in added_modules.items():
            if previous is None:
                # remove the one we added
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module

@pytest.mark.asyncio
async def test_handle_start_command_success(monkeypatch, tmp_path):
    server_utils = load_server_utils_module()

    # Prepare data for extract_command_data to return
    task = "test task"
    report_type = "summary"
    source_urls = ["http://a"]
    document_urls = ["http://doc"]
    tone = "neutral"
    headers = {"Auth": "tok"}
    report_source = "sourceA"
    query_domains = ["a.com"]
    mcp_enabled = True
    mcp_strategy = "strat"
    mcp_configs = {"k": "v"}
    max_search_results = 5

    # Patch extract_command_data to return the above values
    def fake_extract_command_data(json_data):
        return (task, report_type, source_urls, document_urls, tone, headers, report_source, query_domains, mcp_enabled, mcp_strategy, mcp_configs, max_search_results)
    monkeypatch.setattr(server_utils, "extract_command_data", fake_extract_command_data)

    # Create a fake logs handler class
    log_file_path = tmp_path / "logs.json"
    class FakeLogsHandler:
        def __init__(self, websocket, task_arg):
            self.websocket = websocket
            self.task_arg = task_arg
            self.log_file = str(log_file_path)
            self.sent = []

        async def send_json(self, data):
            # record what is sent for assertion
            self.sent.append(data)

    monkeypatch.setattr(server_utils, "CustomLogsHandler", FakeLogsHandler)

    # Patch sanitize_filename to deterministic value
    monkeypatch.setattr(server_utils, "sanitize_filename", lambda s: "sanitized_filename")

    # Create fake manager with start_streaming async method
    class FakeManager:
        def __init__(self):
            self.called_with = None

        async def start_streaming(self, *args, **kwargs):
            self.called_with = args
            return {"result": "ok"}

    manager = FakeManager()

    # Patch generate_report_files to return a dict
    generated_files = {"pdf": str(tmp_path / "report.pdf")}
    async def fake_generate_report_files(report, sanitized_filename):
        # ensure that report is the str of the manager return value
        assert report == str({"result": "ok"})
        assert sanitized_filename == "sanitized_filename"
        return dict(generated_files)  # return a copy
    monkeypatch.setattr(server_utils, "generate_report_files", fake_generate_report_files)

    # Capture what send_file_paths is called with
    captured = {}
    async def fake_send_file_paths(websocket, file_paths):
        captured['websocket'] = websocket
        captured['file_paths'] = dict(file_paths)
    monkeypatch.setattr(server_utils, "send_file_paths", fake_send_file_paths)

    # Prepare a fake websocket (could be any object)
    class DummyWebsocket:
        pass
    ws = DummyWebsocket()

    # Build the data string with a 6-char prefix (the function slices data[6:])
    payload = json.dumps({"irrelevant": "x"})
    data = "START " + payload

    # Call the function under test
    await server_utils.handle_start_command(ws, data, manager)

    # Assertions:
    assert manager.called_with is not None
    assert 'file_paths' in captured
    assert "pdf" in captured['file_paths']
    expected_json_rel = os.path.relpath(str(log_file_path))
    assert captured['file_paths']['json'] == expected_json_rel

@pytest.mark.asyncio
async def test_handle_start_command_missing_task_or_report_type(monkeypatch, capsys):
    server_utils = load_server_utils_module()

    # Patch extract_command_data to return missing task and report_type
    def fake_extract_command_data_missing(json_data):
        return (None, None, [], [], None, None, None, None, False, None, None, None)
    monkeypatch.setattr(server_utils, "extract_command_data", fake_extract_command_data_missing)

    # Ensure CustomLogsHandler is not called; make it raise if invoked
    def raising_custom_logs_handler(*args, **kwargs):
        raise RuntimeError("CustomLogsHandler should not be called when task/report_type missing")
    monkeypatch.setattr(server_utils, "CustomLogsHandler", raising_custom_logs_handler)

    # Also patch other downstream functions to ensure they would error if called
    monkeypatch.setattr(server_utils, "generate_report_files", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not be called")))
    monkeypatch.setattr(server_utils, "send_file_paths", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not be called")))

    # Prepare a fake websocket and manager
    class DummyWebsocket:
        pass
    ws = DummyWebsocket()
    manager = object()

    data = "START " + json.dumps({"some": "data"})
    # Call function
    result = await server_utils.handle_start_command(ws, data, manager)

    # It should return None and print the error message
    assert result is None
    captured = capsys.readouterr()
    assert "Error: Missing task or report_type" in captured.out
