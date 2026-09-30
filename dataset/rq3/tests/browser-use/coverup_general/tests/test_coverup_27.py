# file: browser_use/cli.py:2036-2150
# asked: {"lines": [2036, 2039, 2040, 2042, 2043, 2046, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2057, 2059, 2061, 2063, 2064, 2067, 2069, 2071, 2072, 2075, 2076, 2079, 2080, 2081, 2083, 2084, 2085, 2086, 2088, 2089, 2090, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2123, 2126, 2127, 2128, 2129, 2131, 2133, 2135, 2136, 2137, 2139, 2140, 2141, 2142, 2144, 2145, 2146, 2147, 2149, 2150], "branches": [[2039, 2040], [2039, 2046], [2046, 2048], [2046, 2067], [2067, 2069], [2067, 2075], [2085, 2086], [2085, 2088], [2140, 2141], [2140, 2142], [2146, 2147], [2146, 2150]]}
# gained: {"lines": [2036, 2039, 2040, 2042, 2043, 2046, 2048, 2049, 2050, 2051, 2052, 2053, 2054, 2057, 2059, 2061, 2063, 2064, 2067, 2069, 2071, 2072, 2075, 2076, 2079, 2080, 2081, 2083, 2084, 2085, 2086, 2088, 2089, 2090, 2093, 2094, 2095, 2096, 2097, 2098, 2099, 2100, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2123, 2126, 2127, 2128, 2129, 2131, 2133, 2135, 2136, 2137, 2139, 2140, 2141, 2142, 2144, 2145, 2146, 2147, 2149, 2150], "branches": [[2039, 2040], [2039, 2046], [2046, 2048], [2046, 2067], [2067, 2069], [2067, 2075], [2085, 2086], [2085, 2088], [2140, 2141], [2140, 2142], [2146, 2147]]}

import asyncio
import sys
import types
import logging
import os

import pytest

import browser_use.cli as cli


# Helper to restore root logger handlers after tests that modify them
def _restore_root_handlers(original_handlers):
    root = logging.getLogger()
    # remove all current handlers
    for h in list(root.handlers):
        try:
            root.removeHandler(h)
        except Exception:
            pass
    # re-add original handlers
    for h in original_handlers:
        root.addHandler(h)


def test_version_flag_prints_version_and_exits(monkeypatch, capsys):
    # Patch importlib.metadata.version used dynamically inside function
    import importlib.metadata as md

    monkeypatch.setattr(md, "version", lambda name: "1.2.3")
    # Patch the module-level sys.exit to raise SystemExit so we can assert it was called
    def _exit(code=0):
        raise SystemExit(code)
    monkeypatch.setattr(cli.sys, "exit", _exit)

    # call with version in kwargs (function uses kwargs['version'])
    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=False, version=True)
    assert exc.value.code == 0

    captured = capsys.readouterr()
    assert "1.2.3" in captured.out


def test_mcp_mode_tries_telemetry_and_runs_mcp(monkeypatch):
    # Prepare a dummy ProductTelemetry whose capture raises (to take the except path)
    class DummyTelemetry:
        def __init__(self):
            self.captured = False
        def capture(self, event):
            self.captured = True
            # raise to hit except branch
            raise RuntimeError("telemetry failed")

    monkeypatch.setattr(cli, "ProductTelemetry", DummyTelemetry)
    monkeypatch.setattr(cli, "get_browser_use_version", lambda: "vX.Y")

    # Create a fake module browser_use.mcp.server with async main
    mod_name = "browser_use.mcp.server"
    m = types.ModuleType(mod_name)
    called = {"main": False}
    async def fake_main():
        called["main"] = True
        return None
    m.main = fake_main
    sys.modules[mod_name] = m

    # Run run_main_interface with mcp flag; include version=False to avoid KeyError
    cli.run_main_interface(ctx=None, debug=False, mcp=True, version=False)

    assert called["main"] is True

    # cleanup inserted module
    del sys.modules[mod_name]


def test_prompt_mode_sets_env_and_runs_prompt(monkeypatch):
    # Provide a fake run_prompt_mode coroutine to ensure it's invoked
    called = {"args": None}
    async def fake_prompt(prompt_arg, ctx_arg, debug_arg):
        called["args"] = (prompt_arg, ctx_arg, debug_arg)
        return None

    monkeypatch.setattr(cli, "run_prompt_mode", fake_prompt)

    # Ensure env var is not set, call function
    if "BROWSER_USE_LOGGING_LEVEL" in os.environ:
        del os.environ["BROWSER_USE_LOGGING_LEVEL"]

    cli.run_main_interface(ctx="CTX", debug=True, prompt="PROMPT_VAL", version=False)

    assert os.environ.get("BROWSER_USE_LOGGING_LEVEL") == "result"
    assert called["args"] == ("PROMPT_VAL", "CTX", True)
    # cleanup env var
    if "BROWSER_USE_LOGGING_LEVEL" in os.environ:
        del os.environ["BROWSER_USE_LOGGING_LEVEL"]


def test_load_user_config_failure_prints_and_exits(monkeypatch, capsys):
    # Patch load_user_config to raise
    monkeypatch.setattr(cli, "load_user_config", lambda: (_ for _ in ()).throw(Exception("badcfg")))
    # Patch sys.exit
    def _exit(code=1):
        raise SystemExit(code)
    monkeypatch.setattr(cli.sys, "exit", _exit)

    # Capture and assert; include version=False to avoid KeyError
    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=False, version=False)
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Error loading configuration: badcfg" in captured.out


def test_update_config_with_click_args_failure_prints_and_exits(monkeypatch, capsys):
    # load_user_config returns a config dict
    monkeypatch.setattr(cli, "load_user_config", lambda: {"some": "cfg"})
    # update_config_with_click_args raises
    def bad_update(cfg, ctx):
        raise Exception("bad update")
    monkeypatch.setattr(cli, "update_config_with_click_args", bad_update)
    # Patch sys.exit
    def _exit(code=1):
        raise SystemExit(code)
    monkeypatch.setattr(cli.sys, "exit", _exit)

    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx="CTX", debug=False, version=False)
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Error updating configuration: bad update" in captured.out


def test_save_user_config_failure_prints_and_exits(monkeypatch, capsys):
    # load_user_config returns a config dict
    monkeypatch.setattr(cli, "load_user_config", lambda: {"model": {"name": "m"}, "browser": {"headless": True}})
    # update_config_with_click_args returns config unchanged
    monkeypatch.setattr(cli, "update_config_with_click_args", lambda cfg, ctx: cfg)
    # save_user_config raises
    def bad_save(cfg):
        raise Exception("bad save")
    monkeypatch.setattr(cli, "save_user_config", bad_save)
    # Patch sys.exit
    def _exit(code=1):
        raise SystemExit(code)
    monkeypatch.setattr(cli.sys, "exit", _exit)

    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=False, version=False)
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Error saving configuration: bad save" in captured.out


def test_textual_interface_exception_triggers_cleanup_and_exits(monkeypatch, capsys):
    # Prepare environment for normal flow up to textual_interface
    monkeypatch.setattr(cli, "load_user_config", lambda: {"model": {"name": "m"}, "browser": {"headless": False}})
    monkeypatch.setattr(cli, "update_config_with_click_args", lambda cfg, ctx: cfg)
    monkeypatch.setattr(cli, "save_user_config", lambda cfg: None)

    # Make textual_interface raise to hit the final except branch
    def bad_textual(config):
        raise Exception("ui fail")
    monkeypatch.setattr(cli, "textual_interface", bad_textual)

    # Patch sys.exit to raise so we can assert after it runs
    def _exit(code=1):
        raise SystemExit(code)
    monkeypatch.setattr(cli.sys, "exit", _exit)

    # Save original handlers to restore later
    root = logging.getLogger()
    original_handlers = list(root.handlers)

    # Run with debug True to also execute traceback.print_exc branch; include version=False
    with pytest.raises(SystemExit) as exc:
        cli.run_main_interface(ctx=None, debug=True, version=False)
    assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "Error launching Browser-Use: ui fail" in captured.out

    # Ensure that handlers were restored to something reasonable; now restore original handlers to avoid contamination
    _restore_root_handlers(original_handlers)
