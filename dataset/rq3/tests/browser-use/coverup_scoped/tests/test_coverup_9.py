# file: browser_use/cli.py:2036-2150
# asked: {"lines": [2036, 2039, 2040, 2042, 2043, 2046, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2057, 2059, 2061, 2063, 2064, 2067, 2069, 2071, 2072, 2075, 2076, 2079, 2080, 2081, 2083, 2084, 2085, 2086, 2088, 2089, 2090, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2123, 2126, 2127, 2128, 2129, 2131, 2133, 2135, 2136, 2137, 2139, 2140, 2141, 2142, 2144, 2145, 2146, 2147, 2149, 2150], "branches": [[2039, 2040], [2039, 2046], [2046, 2048], [2046, 2067], [2067, 2069], [2067, 2075], [2085, 2086], [2085, 2088], [2140, 2141], [2140, 2142], [2146, 2147], [2146, 2150]]}
# gained: {"lines": [2036, 2039, 2040, 2042, 2043, 2046, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2061, 2063, 2064, 2067, 2069, 2071, 2072, 2075, 2076, 2079, 2080, 2081, 2083, 2084, 2085, 2086, 2088, 2089, 2090, 2093, 2094, 2095, 2096, 2103, 2104, 2105, 2106, 2113, 2114, 2115, 2116, 2123, 2126, 2127, 2128, 2129, 2131, 2133, 2135, 2136, 2137, 2139, 2140, 2141, 2142, 2144, 2145, 2146, 2147, 2149, 2150], "branches": [[2039, 2040], [2039, 2046], [2046, 2048], [2046, 2067], [2067, 2069], [2067, 2075], [2085, 2086], [2140, 2141], [2140, 2142], [2146, 2147]]}

import sys
import types
import asyncio
import importlib.metadata
import logging

import pytest

import browser_use.cli as cli


def test_version_branch_prints_and_exits(monkeypatch, capsys):
    # Arrange: patch importlib.metadata.version to return predictable version
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "9.9.9")
    # Make sys.exit raise SystemExit so we can assert on it
    monkeypatch.setattr(sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code)))
    # Act / Assert
    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=False, version=True)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "9.9.9" in captured.out


def test_mcp_branch_runs_telemetry_and_mcp_main(monkeypatch):
    called = {"telemetry_captured": False, "mcp_main_ran": False}

    # Dummy ProductTelemetry implementation to capture call
    class DummyTelemetry:
        def capture(self, event):
            # ensure event has some expected attributes
            assert hasattr(event, "version")
            assert getattr(event, "action", None) == "start"
            assert getattr(event, "mode", None) == "mcp_server"
            called["telemetry_captured"] = True

    # Provide a dummy async mcp_main
    async def dummy_mcp_main():
        called["mcp_main_ran"] = True

    # Inject dummy telemetry class and version getter
    monkeypatch.setattr(cli, "ProductTelemetry", DummyTelemetry)
    monkeypatch.setattr(cli, "get_browser_use_version", lambda: "vX")
    # Inject a fake module for browser_use.mcp.server with attribute main
    fake_module = types.SimpleNamespace(main=dummy_mcp_main)
    monkeypatch.setitem(sys.modules, "browser_use.mcp.server", fake_module)

    # Act
    # Include 'version' key to avoid KeyError in run_main_interface
    cli.run_main_interface(ctx=None, debug=False, mcp=True, version=False)

    # Assert
    assert called["telemetry_captured"] is True
    assert called["mcp_main_ran"] is True


def test_prompt_branch_sets_env_and_runs_prompt(monkeypatch):
    called = {"ran": False, "args": None}

    async def dummy_prompt(prompt_arg, ctx_arg, debug_arg):
        # check that run_main_interface passed the values
        called["args"] = (prompt_arg, ctx_arg, debug_arg)
        called["ran"] = True

    monkeypatch.setattr(cli, "run_prompt_mode", dummy_prompt)
    # Act: include 'version' key to satisfy run_main_interface
    cli.run_main_interface(ctx="CTX", debug=True, prompt="PROMPT_VALUE", version=False)

    # Assert env var set and prompt ran
    assert called["ran"] is True
    assert called["args"] == ("PROMPT_VALUE", "CTX", True)
    assert cli.os.environ.get("BROWSER_USE_LOGGING_LEVEL") == "result"
    # Clean up env var to avoid pollution
    monkeypatch.delenv("BROWSER_USE_LOGGING_LEVEL", raising=False)


def test_textual_interface_exception_restores_logging_and_exits_with_traceback(monkeypatch, capsys):
    # Prepare config to be returned by load_user_config
    config = {"model": {"name": "mymodel"}, "browser": {"headless": True}}

    # Patch config-related functions to return the test config and to be no-ops
    monkeypatch.setattr(cli, "load_user_config", lambda: config)
    monkeypatch.setattr(cli, "update_config_with_click_args", lambda c, ctx: c)
    monkeypatch.setattr(cli, "save_user_config", lambda c: None)

    # Make textual_interface async function that raises to trigger the except block
    async def raising_textual_interface(cfg):
        raise RuntimeError("boom-boom")

    monkeypatch.setattr(cli, "textual_interface", raising_textual_interface)

    # Replace sys.exit to raise SystemExit so the test can catch it
    monkeypatch.setattr(sys, "exit", lambda code=1: (_ for _ in ()).throw(SystemExit(code)))

    # Capture logger handlers before running to compare restoration behavior
    root_logger = logging.getLogger()
    before_handlers = list(root_logger.handlers)

    # Run and assert SystemExit with code 1 and that traceback printed when debug True
    with pytest.raises(SystemExit) as exc:
        # include version key to avoid KeyError
        cli.run_main_interface(ctx=None, debug=True, prompt=False, mcp=False, version=False)

    assert exc.value.code == 1

    # Ensure that error message was printed and traceback printed due to debug=True
    captured = capsys.readouterr()
    # Error message may be on stdout or stderr; check both
    combined = (captured.out or "") + (captured.err or "")
    assert "Error launching Browser-Use: boom-boom" in combined or "boom-boom" in combined
    # Traceback should include 'Traceback' when debug True (print_exc goes to stderr)
    assert "Traceback (most recent call last)" in combined

    # Ensure logger handlers restored to at least include one handler after error handling
    assert len(root_logger.handlers) >= 1

    # Clean-up: restore original handlers to avoid side effects for other tests
    root_logger.handlers = before_handlers
