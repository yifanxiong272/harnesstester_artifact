# file: tests/disabled_test_mcp.py:217-261
# asked: {"lines": [217, 219, 220, 223, 224, 225, 227, 230, 233, 234, 235, 238, 239, 240, 243, 244, 246, 247, 249, 250, 251, 252, 253, 255, 257, 258, 259, 261], "branches": [[223, 224], [223, 227], [249, 250], [249, 255], [252, 249], [252, 253], [257, 258], [257, 261]]}
# gained: {"lines": [217, 219, 220, 223, 224, 225, 227, 230, 233, 234, 235, 238, 239, 240, 243, 244, 246, 247, 249, 250, 251, 252, 253, 255, 257, 258, 259, 261], "branches": [[223, 224], [223, 227], [249, 250], [249, 255], [252, 249], [252, 253], [257, 258], [257, 261]]}

import sys
import types
from pathlib import Path
import importlib.util

import pytest


def load_disabled_test_module(monkeypatch):
    """
    Locate the existing disabled_test_mcp.py in the repository and load it as
    gpt_researcher.tests.disabled_test_mcp so that coverage attributes point to
    the real file and its lines (217-261) can be executed.
    """
    candidates = list(Path(".").rglob("disabled_test_mcp.py"))
    if not candidates:
        # If the real file is not present, raise so tests fail clearly.
        raise FileNotFoundError("Could not find disabled_test_mcp.py in repository tree")

    path = candidates[0].resolve()

    module_name = "gpt_researcher.tests.disabled_test_mcp"
    pkg_name = "gpt_researcher"
    subpkg_name = "gpt_researcher.tests"

    # Ensure package entries exist in sys.modules so relative imports inside file (if any) work
    if pkg_name not in sys.modules:
        monkeypatch.setitem(sys.modules, pkg_name, types.ModuleType(pkg_name))
    if subpkg_name not in sys.modules:
        monkeypatch.setitem(sys.modules, subpkg_name, types.ModuleType(subpkg_name))

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    module = importlib.util.module_from_spec(spec)
    # Insert into sys.modules before exec to support imports referencing this module
    monkeypatch.setitem(sys.modules, module_name, module)
    # Execute module code in its own namespace
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_main_environment_setup_fails(monkeypatch, capsys):
    mod = load_disabled_test_module(monkeypatch)

    # Patch setup_environment to return False
    monkeypatch.setattr(mod, "setup_environment", lambda: False, raising=False)

    # Ensure MCP test functions would raise if called (they should not be)
    async def _fail_called(*_, **__):
        raise AssertionError("MCP test function should not be called when environment setup fails")

    # If the attributes don't exist on the loaded module, set them to our stubs
    if not hasattr(mod, "test_web_search_mcp"):
        mod.test_web_search_mcp = _fail_called
    else:
        monkeypatch.setattr(mod, "test_web_search_mcp", _fail_called, raising=False)

    if not hasattr(mod, "test_github_mcp"):
        mod.test_github_mcp = _fail_called
    else:
        monkeypatch.setattr(mod, "test_github_mcp", _fail_called, raising=False)

    # Run main (async)
    result = await mod.main()

    # main should return None (early return)
    assert result is None

    # Capture output and assert expected failure messages are present
    captured = capsys.readouterr()
    assert "Testing MCP Integration with GPT Researcher" in captured.out
    assert "Environment setup failed" in captured.out
    # Should not reach the "Environment setup complete" message
    assert "Environment setup complete" not in captured.out


@pytest.mark.asyncio
async def test_main_all_mcp_pass(monkeypatch, capsys):
    mod = load_disabled_test_module(monkeypatch)

    # Patch setup_environment to return True
    monkeypatch.setattr(mod, "setup_environment", lambda: True, raising=False)

    # Async stubs for MCP tests returning True
    async def _true(*_, **__):
        return True

    monkeypatch.setattr(mod, "test_web_search_mcp", _true, raising=False)
    monkeypatch.setattr(mod, "test_github_mcp", _true, raising=False)

    # Run main
    result = await mod.main()

    # main should return None
    assert result is None

    captured = capsys.readouterr()
    # Check that both test names appear and are marked PASSED
    assert "Web Search MCP" in captured.out
    assert "GitHub MCP" in captured.out
    assert "Overall: 2/2 tests passed" in captured.out
    # Success celebratory messages should be present
    assert "All MCP integration tests completed successfully" in captured.out
    assert "Both Web Search (news) and GitHub (code) MCP servers work seamlessly" in captured.out


@pytest.mark.asyncio
async def test_main_some_mcp_fail(monkeypatch, capsys):
    mod = load_disabled_test_module(monkeypatch)

    # Patch setup_environment to return True
    monkeypatch.setattr(mod, "setup_environment", lambda: True, raising=False)

    # Make web search pass and github fail
    async def _true(*_, **__):
        return True

    async def _false(*_, **__):
        return False

    monkeypatch.setattr(mod, "test_web_search_mcp", _true, raising=False)
    monkeypatch.setattr(mod, "test_github_mcp", _false, raising=False)

    # Run main
    result = await mod.main()

    assert result is None

    captured = capsys.readouterr()
    # Should show 1/2 tests passed
    assert "Overall: 1/2 tests passed" in captured.out
    # Warning line should be printed (the else branch)
    assert "Some tests failed" in captured.out or "⚠️ Some tests failed" in captured.out
    # Ensure one test is reported as PASSED and the other as FAILED
    assert "Web Search MCP" in captured.out
    assert "GitHub MCP" in captured.out
    assert "✅ PASSED" in captured.out
    assert "❌ FAILED" in captured.out
