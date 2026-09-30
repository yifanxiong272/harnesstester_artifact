# file: tests/disabled_test_mcp.py:155-215
# asked: {"lines": [155, 157, 158, 160, 161, 164, 167, 168, 169, 170, 173, 174, 175, 178, 179, 181, 182, 185, 186, 188, 189, 192, 193, 194, 195, 196, 197, 198, 200, 203, 204, 205, 206, 207, 208, 210, 212, 213, 214, 215], "branches": []}
# gained: {"lines": [155, 157, 158, 160, 161, 164, 167, 168, 169, 170, 173, 174, 175, 178, 179, 181, 182, 185, 186, 188, 189, 192, 193, 194, 195, 196, 197, 198, 200, 203, 204, 205, 206, 207, 208, 210, 212, 213, 214, 215], "branches": []}

import sys
import types
import builtins
import importlib.util
from pathlib import Path
import pytest

def _find_disabled_test_file():
    # Search for disabled_test_mcp.py in the repository tree
    cwd = Path.cwd()
    matches = list(cwd.rglob("disabled_test_mcp.py"))
    if not matches:
        raise FileNotFoundError("Could not find disabled_test_mcp.py in the repository tree")
    # Prefer a path that includes "gpt-researcher" or "gpt_researcher" if available, otherwise first match
    for p in matches:
        if "gpt-researcher" in str(p) or "gpt_researcher" in str(p):
            return p
    return matches[0]

def _load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    # Execute the module in its own namespace
    loader = spec.loader
    assert loader is not None
    loader.exec_module(mod)
    return mod

@pytest.mark.asyncio
async def test_execute_original_test_success(monkeypatch, tmp_path):
    """
    Load the real disabled_test_mcp.py file and execute its test_github_mcp function
    to exercise lines 155-215 (success path). Provide a fake gpt_researcher.GPTResearcher
    and redirect the report file write to tmp_path to avoid polluting repo.
    """
    file_path = _find_disabled_test_file()
    mod = _load_module_from_path(file_path, "loaded_disabled_test_mcp")

    # Provide a fake GPTResearcher used by the loaded module
    class FakeGPTResearcher:
        def __init__(self, query: str, mcp_configs=None, **kwargs):
            self.query = query
            self.mcp_configs = mcp_configs
            self._costs = 3.1415

        async def conduct_research(self, on_progress=None):
            return {"ctx": "context for " + self.query}

        async def write_report(self, *args, **kwargs):
            return f"REPORT for: {self.query}\nMCP:{self.mcp_configs}"

        def get_costs(self):
            return self._costs

    fake_pkg = types.ModuleType("gpt_researcher")
    fake_pkg.GPTResearcher = FakeGPTResearcher

    # Inject into sys.modules so "from gpt_researcher import GPTResearcher" inside module resolves
    monkeypatch.setitem(sys.modules, "gpt_researcher", fake_pkg)

    # Redirect writes of the report filename used in the original function to a tmp path
    report_target_path = tmp_path / "test_github_mcp_report.md"
    original_open = builtins.open

    def fake_open(name, mode="r", *args, **kwargs):
        if isinstance(name, str) and name.endswith("test_github_mcp_report.md"):
            return original_open(report_target_path, mode, *args, **kwargs)
        return original_open(name, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open, raising=True)

    # Run the function defined in the loaded module
    # The function in file is async def test_github_mcp()
    result = await mod.test_github_mcp()
    assert result is True

    # Confirm file written and content matches fake reporter
    assert report_target_path.exists()
    content = report_target_path.read_text(encoding="utf-8")
    assert "REPORT for:" in content
    assert "MCP" in content

    # Ensure the injected fake was used
    assert "gpt_researcher" in sys.modules

@pytest.mark.asyncio
async def test_execute_original_test_exception_branch(monkeypatch):
    """
    Execute the loaded original test function but make GPTResearcher constructor raise,
    so the except branch (lines 212-215) runs. Verify the function returns False and
    that the module's logger.exception is invoked.
    """
    file_path = _find_disabled_test_file()
    mod = _load_module_from_path(file_path, "loaded_disabled_test_mcp_exc")

    # Create a gpt_researcher module whose GPTResearcher raises on init
    class RaisingGPTResearcher:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("intentional init failure")

    fake_pkg = types.ModuleType("gpt_researcher")
    fake_pkg.GPTResearcher = RaisingGPTResearcher
    monkeypatch.setitem(sys.modules, "gpt_researcher", fake_pkg)

    # Replace the module's logger with a dummy that records exception calls
    class DummyLogger:
        def __init__(self):
            self.called = False
            self.last_msg = None
        def exception(self, msg, *args, **kwargs):
            self.called = True
            self.last_msg = msg

    dummy_logger = DummyLogger()
    # If the loaded module already has logger, override it; otherwise set it
    setattr(mod, "logger", dummy_logger)

    # Run the function; because constructor raises, it should hit except and return False
    result = await mod.test_github_mcp()
    assert result is False
    assert dummy_logger.called is True
    # The message passed in the original code is "GitHub MCP test error:"
    assert "GitHub MCP test error" in (dummy_logger.last_msg or "GitHub MCP test error")
