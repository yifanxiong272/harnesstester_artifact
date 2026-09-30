import asyncio
import logging
import os
import importlib.metadata as _md
import sys
import types
import pytest

import browser_use.cli as cli

# Helper to run coroutines deterministically in tests by creating a fresh loop.
def _run_coroutine_sync(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_version_flag_round_019(monkeypatch, capsys):
    # Ensure importlib.metadata.version is used and sys.exit(0) is raised after printing
    monkeypatch.setattr(_md, "version", lambda name: "1.2.3")
    # Ensure asyncio.run isn't replaced here, but patch it defensively
    monkeypatch.setattr(cli, "asyncio", cli.asyncio)

    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=False, version=True)
    assert exc.value.code == 0

    captured = capsys.readouterr()
    assert "1.2.3" in captured.out


def test_mcp_mode_success_round_019(monkeypatch):
    # Patch ProductTelemetry to capture the event without raising
    class DummyTelemetry:
        last_instance = None
        def __init__(self):
            DummyTelemetry.last_instance = self
            self.captured = None
        def capture(self, event):
            self.captured = event

    monkeypatch.setattr(cli, "ProductTelemetry", DummyTelemetry)

    # Provide a simple async mcp_main to be run. Because the code does a local import
    # from browser_use.mcp.server import main as mcp_main, we must provide that module in sys.modules.
    async def dummy_mcp_main():
        return "mcp_ok"

    fake_module = types.ModuleType("browser_use.mcp.server")
    fake_module.main = dummy_mcp_main
    monkeypatch.setitem(sys.modules, "browser_use.mcp.server", fake_module)

    # Replace asyncio.run with a deterministic runner
    monkeypatch.setattr(cli, "asyncio", type("A", (), {"run": staticmethod(_run_coroutine_sync)}))

    # Call with mcp mode enabled; should return normally after running mcp_main
    result = cli.run_main_interface(ctx=None, debug=False, version=False, mcp=True)
    assert result is None
    # Ensure telemetry instance captured an event object
    assert DummyTelemetry.last_instance is not None
    assert getattr(DummyTelemetry.last_instance, "captured") is not None


def test_mcp_mode_telemetry_exception_round_019(monkeypatch):
    # Patch ProductTelemetry to raise during capture to hit the exception/pass branch
    class DummyTelemetryRaises:
        last_instance = None
        def __init__(self):
            DummyTelemetryRaises.last_instance = self
        def capture(self, event):
            raise RuntimeError("telemetry failed")

    monkeypatch.setattr(cli, "ProductTelemetry", DummyTelemetryRaises)

    called = {}

    async def dummy_mcp_main():
        # mark that mcp_main was executed
        called['mcp_called'] = True
        return "mcp_ok"

    fake_module = types.ModuleType("browser_use.mcp.server")
    fake_module.main = dummy_mcp_main
    monkeypatch.setitem(sys.modules, "browser_use.mcp.server", fake_module)

    monkeypatch.setattr(cli, "asyncio", type("A", (), {"run": staticmethod(_run_coroutine_sync)}))

    # Should swallow telemetry exception and still run mcp_main without raising
    res = cli.run_main_interface(ctx=None, debug=False, version=False, mcp=True)
    assert res is None
    assert called.get('mcp_called') is True


def test_prompt_mode_round_019(monkeypatch):
    # Capture that run_prompt_mode was invoked with expected args
    recorded = {}

    async def fake_prompt(prompt, ctx, debug):
        recorded['prompt'] = prompt
        recorded['ctx'] = ctx
        recorded['debug'] = debug
        return "ok"

    monkeypatch.setattr(cli, "run_prompt_mode", fake_prompt)
    monkeypatch.setattr(cli, "asyncio", type("A", (), {"run": staticmethod(_run_coroutine_sync)}))

    # Ensure env var is not set beforehand
    os.environ.pop('BROWSER_USE_LOGGING_LEVEL', None)

    res = cli.run_main_interface(ctx="CTX", debug=True, version=False, prompt="my_prompt")
    assert res is None
    # Environment variable should be set to 'result'
    assert os.environ.get('BROWSER_USE_LOGGING_LEVEL') == 'result'
    # run_prompt_mode should have been called with provided args
    assert recorded.get('prompt') == 'my_prompt'
    assert recorded.get('ctx') == 'CTX'
    assert recorded.get('debug') is True


def test_config_load_failure_round_019(monkeypatch, capsys):
    # Simulate load_user_config raising to hit config load error path -> sys.exit(1)
    def fake_load_user_config():
        raise RuntimeError("bad config")

    monkeypatch.setattr(cli, "load_user_config", fake_load_user_config)
    # Avoid running asyncio parts
    monkeypatch.setattr(cli, "asyncio", type("A", (), {"run": staticmethod(_run_coroutine_sync)}))

    with pytest.raises(SystemExit) as excinfo:
        cli.run_main_interface(ctx=None, debug=False, version=False)
    assert excinfo.value.code == 1

    out = capsys.readouterr().out
    assert "Error loading configuration" in out
    assert "bad config" in out


def test_textual_interface_error_debug_round_019(monkeypatch, capsys):
    # Simulate success through config/load/update/save then textual_interface raising
    monkeypatch.setattr(cli, "load_user_config", lambda: {"model": {"name": "m"}, "browser": {"headless": False}})
    monkeypatch.setattr(cli, "update_config_with_click_args", lambda c, ctx: c)
    monkeypatch.setattr(cli, "save_user_config", lambda c: None)

    async def fake_textual_interface(config):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "textual_interface", fake_textual_interface)
    monkeypatch.setattr(cli, "asyncio", type("A", (), {"run": staticmethod(_run_coroutine_sync)}))

    # Run with debug=True to hit the traceback-printing branch
    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=True, version=False)
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Error launching Browser-Use: boom" in captured.out
