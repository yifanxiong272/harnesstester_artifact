import importlib
import types
import pytest

import browser_use.cli as cli


def _get_main_callback():
    """Return the underlying function object for the click-decorated `main`.

    Click's @pass_context wraps the original function in a wrapper that calls
    get_current_context(), which fails when no active Click context is present.
    To avoid requiring an active Click context in unit tests, unwrap the
    decorated callback and return the original function (if available).
    """
    cb = getattr(cli.main, "callback", cli.main)
    # If the callback is decorated, the original function is usually stored
    # in __wrapped__. Use it to bypass Click's context-requiring wrapper.
    return getattr(cb, "__wrapped__", cb)


class DummyCtx:
    def __init__(self, invoked_subcommand):
        # only attribute the cli.main uses
        self.invoked_subcommand = invoked_subcommand


def test_template_generation_round_117(monkeypatch):
    """When kwargs contains 'template', _run_template_generation should be
    invoked with (template, output, force) and run_main_interface must NOT be
    called. This covers lines ~2027-2029.
    """
    called = {"template": None, "run_main_interface": False}

    def fake_run_template_generation(template, output, force):
        # record values exactly as passed
        called["template"] = (template, output, force)

    def fake_run_main_interface(*args, **kwargs):
        called["run_main_interface"] = True

    monkeypatch.setattr(cli, "_run_template_generation", fake_run_template_generation)
    monkeypatch.setattr(cli, "run_main_interface", fake_run_main_interface)

    main_fn = _get_main_callback()

    ctx = DummyCtx(invoked_subcommand=None)
    # pass template and ensure force True is passed through
    kwargs = {"template": "advanced", "output": "out_file.py", "force": True}

    # Call the underlying original function (unwrapped) as it would be invoked programmatically
    result = main_fn(ctx, debug=False, **kwargs)

    # After calling, template generator must have been called with exact args
    assert called["template"] == ("advanced", "out_file.py", True)
    # run_main_interface must not have been called in this branch
    assert called["run_main_interface"] is False
    # the function returns (explicitly or implicitly) None after template
    assert result is None


def test_no_template_invoked_subcommand_none_round_117(monkeypatch):
    """When no template is provided and ctx.invoked_subcommand is None,
    run_main_interface must be invoked with (ctx, debug, **kwargs).
    This covers lines ~2031->2033.
    """
    recorded = {"called": False, "args": None, "kwargs": None}

    def fake_run_main_interface(ctx, debug_arg, **kw):
        recorded["called"] = True
        # record reference identity for ctx and passed args
        recorded["args"] = (ctx, debug_arg)
        recorded["kwargs"] = kw

    # Ensure template generator is not accidentally invoked
    def fake_run_template_generation(*a, **k):
        raise AssertionError("_run_template_generation should not be called in this test")

    monkeypatch.setattr(cli, "run_main_interface", fake_run_main_interface)
    monkeypatch.setattr(cli, "_run_template_generation", fake_run_template_generation)

    main_fn = _get_main_callback()

    ctx = DummyCtx(invoked_subcommand=None)
    kwargs = {"model": "gpt-5-mini", "debug": True}

    # Call the unwrapped original function; pass debug True explicitly to ensure it's forwarded
    result = main_fn(ctx, debug=True, **{k: v for k, v in kwargs.items() if k != "debug"})

    assert recorded["called"] is True
    # ctx object must be the same instance passed
    assert recorded["args"][0] is ctx
    # debug must be passed as True
    assert recorded["args"][1] is True
    # the kwargs forwarded into run_main_interface must include the other keys
    assert recorded["kwargs"].get("model") == "gpt-5-mini"
    assert result is None


def test_no_template_with_invoked_subcommand_present_round_117(monkeypatch):
    """When no template and ctx.invoked_subcommand is NOT None, neither
    _run_template_generation nor run_main_interface should be called. This
    covers the branch where execution skips the main interface (2031->-1990).
    """
    calls = {"template": 0, "run_main_interface": 0}

    def fake_run_template_generation(*a, **k):
        calls["template"] += 1

    def fake_run_main_interface(*a, **k):
        calls["run_main_interface"] += 1

    monkeypatch.setattr(cli, "_run_template_generation", fake_run_template_generation)
    monkeypatch.setattr(cli, "run_main_interface", fake_run_main_interface)

    main_fn = _get_main_callback()

    # Simulate a subcommand having been invoked
    ctx = DummyCtx(invoked_subcommand="some_subcmd")

    result = main_fn(ctx, debug=False)

    # Neither helper should be called because template is absent and a
    # subcommand was invoked
    assert calls["template"] == 0
    assert calls["run_main_interface"] == 0
    assert result is None
