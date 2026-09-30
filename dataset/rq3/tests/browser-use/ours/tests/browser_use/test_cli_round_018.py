import sys
import types
import logging
import asyncio
import traceback
import importlib.metadata
import types as _types
import pytest

import browser_use.cli as cli
from browser_use.cli import run_main_interface


def test_version_flag_round_018(monkeypatch, capsys):
    """When version flag is set, importlib.metadata.version is invoked and sys.exit(0) is called."""
    # Patch importlib.metadata.version that will be imported inside the function
    monkeypatch.setattr(importlib.metadata, 'version', lambda name: '1.2.3')

    # Patch sys.exit to raise SystemExit so we can assert the exit code
    def _fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(sys, 'exit', _fake_exit)

    # Call function with version flag
    with pytest.raises(SystemExit) as excinfo:
        run_main_interface(ctx={}, debug=False, version=True)

    # Confirm exit code and printed version
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert '1.2.3' in captured.out


def test_mcp_telemetry_and_run_round_018(monkeypatch):
    """When mcp=True, telemetry is attempted (errors ignored) and MCP server main is run via asyncio.run."""
    instantiated = {'count': 0}

    # Dummy ProductTelemetry whose capture raises to exercise the except: pass branch
    class DummyProductTelemetry:
        def __init__(self):
            instantiated['count'] += 1

        def capture(self, ev):
            raise Exception('telemetry-fail')

    # Replace CLITelemetryEvent with simple constructor that records args
    def dummy_cli_event(**kwargs):
        return kwargs

    monkeypatch.setattr(cli, 'ProductTelemetry', DummyProductTelemetry)
    monkeypatch.setattr(cli, 'CLITelemetryEvent', dummy_cli_event)

    # Provide a fake module at browser_use.mcp.server with async main
    mod = _types.ModuleType('browser_use.mcp.server')

    async def fake_mcp_main():
        # coroutine to be consumed by asyncio.run
        return 'mcp_started'

    mod.main = fake_mcp_main
    sys.modules['browser_use.mcp.server'] = mod

    # Capture calls to asyncio.run
    run_called = {'called': False, 'arg': None}

    def fake_asyncio_run(arg):
        run_called['called'] = True
        run_called['arg'] = arg
        return 'ok'

    monkeypatch.setattr(cli.asyncio, 'run', fake_asyncio_run)

    # Run
    run_main_interface(ctx={}, debug=False, mcp=True)

    # Assertions: telemetry constructor was used and asyncio.run got a coroutine
    assert instantiated['count'] == 1
    assert run_called['called'] is True
    # The argument passed to asyncio.run should be a coroutine object (has __await__)
    assert hasattr(run_called['arg'], '__await__')


def test_textual_interface_exception_resets_handlers_debug_round_018(monkeypatch, capsys):
    """Simulate normal init path up to textual_interface, then asyncio.run raises -> handlers reset and sys.exit(1).

    Verifies that the root logger ends up with a single StreamHandler attached to sys.stdout and that
    an error message including the exception is printed. Also exercises the debug traceback printing path.
    """
    # Ensure the function will not take version/mcp/prompt branches
    kwargs = {}

    # Patch load_dotenv to noop
    monkeypatch.setattr(cli, 'load_dotenv', lambda: None)

    # Provide a minimal config that the code expects
    config = {'model': {'name': 'dummy-model'}, 'browser': {'headless': True}}
    monkeypatch.setattr(cli, 'load_user_config', lambda: config)
    monkeypatch.setattr(cli, 'update_config_with_click_args', lambda c, ctx: c)
    monkeypatch.setattr(cli, 'save_user_config', lambda c: None)

    # Patch asyncio.run to throw an exception to trigger the textual_interface except block
    def fake_asyncio_run(arg):
        raise Exception('textual-error')

    monkeypatch.setattr(cli.asyncio, 'run', fake_asyncio_run)

    # Patch traceback.print_exc to avoid long prints and to record it was called
    tb_called = {'ok': False}

    def fake_print_exc():
        tb_called['ok'] = True

    # Since traceback is imported only inside the except when debug=True, patch the global module
    monkeypatch.setattr(traceback, 'print_exc', fake_print_exc)

    # Patch sys.exit to raise SystemExit so we can assert exit code
    def _fake_exit(code=1):
        raise SystemExit(code)

    monkeypatch.setattr(sys, 'exit', _fake_exit)

    # Prepare root logger: set a known handler state and restore later
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    try:
        # Reset handlers to a known single non-stdout handler so we can detect removal
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)
        root_logger.addHandler(logging.StreamHandler(sys.stderr))

        with pytest.raises(SystemExit) as ex:
            run_main_interface(ctx={}, debug=True, **kwargs)

        # Confirm exit code 1
        assert ex.value.code == 1

        # Captured printed output contains our textual-error message
        captured = capsys.readouterr()
        assert 'Error launching Browser-Use: textual-error' in captured.out

        # After exception handling, the root logger should have had its handlers cleared and console_handler re-added
        handlers = list(root_logger.handlers)
        assert len(handlers) >= 1
        # At least one handler should be a StreamHandler pointed at sys.stdout (the console_handler re-added)
        assert any(isinstance(h, logging.StreamHandler) and getattr(h, 'stream', None) is sys.stdout for h in handlers)

        # Because debug=True, our fake_print_exc should have been called
        assert tb_called['ok'] is True

    finally:
        # Restore original handlers to avoid affecting other tests
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)
        for h in original_handlers:
            root_logger.addHandler(h)
