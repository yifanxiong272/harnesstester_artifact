import importlib
import sys

import pytest


def _setup_fakes(monkeypatch):
    """Patch symbols in the target module and return (module, recorder dict).

    We patch:
    - module.__doc__ to ensure the assert in run_from_cli passes
    - BasicCLI to a lightweight fake that records the args passed to get_config
    - ConfigHelper to return a deterministic help string
    - run_from_config to record the config it receives instead of executing real logic
    """
    mod = importlib.import_module("sweagent.run.run_batch")

    # Recorder for assertions
    recorder = {}

    # Ensure module docstring is present to satisfy assert __doc__ is not None
    monkeypatch.setattr(mod, "__doc__", "dummy docstring", False)

    class FakeBasicCLI:
        def __init__(self, *init_args, help_text=None):
            # capture provided help_text for later verification
            self._help_text = help_text

        def get_config(self, args):
            # Record a copy of args for deterministic checks
            recorder["basiccli_args"] = list(args) if args is not None else None
            # Return a simple sentinel config that run_from_config should receive
            return {"_fake_config": True, "args": recorder["basiccli_args"], "help": self._help_text}

    monkeypatch.setattr(mod, "BasicCLI", FakeBasicCLI)

    class FakeConfigHelper:
        def get_help(self, cfg):
            # Record which config class was requested for help generation
            recorder["help_requested_for"] = cfg
            return "FAKE_HELP_TEXT"

    monkeypatch.setattr(mod, "ConfigHelper", FakeConfigHelper)

    def fake_run_from_config(cfg):
        # Record the config passed in lieu of executing real run logic
        recorder["run_from_config_called_with"] = cfg

    monkeypatch.setattr(mod, "run_from_config", fake_run_from_config)

    return mod, recorder


def test_run_from_cli_args_none_round_126(monkeypatch):
    """When args is None, run_from_cli should use sys.argv[1:] and pass them to BasicCLI.get_config.

    This covers the branch where args is None -> args = sys.argv[1:].
    """
    mod, rec = _setup_fakes(monkeypatch)

    # Set a deterministic sys.argv (simulate CLI invocation)
    monkeypatch.setattr(sys, "argv", ["progname", "arg1", "arg2"])

    # Call under test with args=None so it takes sys.argv[1:]
    mod.run_from_cli(None)

    # Assertions / oracle:
    # - BasicCLI.get_config saw the argv tail
    assert rec["basiccli_args"] == ["arg1", "arg2"]
    # - run_from_config was invoked with the sentinel config returned by our FakeBasicCLI
    assert rec.get("run_from_config_called_with") is not None
    assert rec["run_from_config_called_with"]["_fake_config"] is True
    assert rec["run_from_config_called_with"]["args"] == ["arg1", "arg2"]
    # - ConfigHelper.get_help was invoked with the RunBatchConfig class from the module
    assert rec.get("help_requested_for") == mod.RunBatchConfig


def test_run_from_cli_args_provided_round_126(monkeypatch):
    """When args is provided, run_from_cli should use that list and not sys.argv.

    This covers the direct-call branch (args is not None).
    """
    mod, rec = _setup_fakes(monkeypatch)

    provided = ["x", "y"]
    # Also set sys.argv to a different value to ensure provided overrides it
    monkeypatch.setattr(sys, "argv", ["progname", "not_used"])

    mod.run_from_cli(provided)

    # BasicCLI.get_config must have received the provided args unchanged
    assert rec["basiccli_args"] == provided
    # run_from_config must have been called with the sentinel config containing the same args
    assert rec.get("run_from_config_called_with") is not None
    assert rec["run_from_config_called_with"]["args"] == provided
