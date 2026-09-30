import sys
import types
import pytest

import sweagent.run.run_single as rs


def test_args_none_round_128(monkeypatch):
    """When args is None, run_from_cli should use sys.argv[1:] and pass that
    result through BasicCLI.get_config into run_from_config.
    """
    captured = {}

    class DummyConfigHelper:
        def get_help(self, cfg):
            # return a deterministic help string
            return "DUMMY_HELP"

    class DummyCLI:
        def __init__(self, cfg_cls, help_text=None):
            # preserve constructor signature; store for inspection if needed
            self.cfg_cls = cfg_cls
            self.help_text = help_text
            self.called_with = None

        def get_config(self, args):
            # mirror shape expected downstream: return an object representing config
            self.called_with = list(args)
            return {"source": "DummyCLI.get_config", "args": list(args)}

    def fake_run_from_config(cfg):
        # capture the exact object passed to run_from_config for assertions
        captured["cfg"] = cfg

    # Patch module-level symbols where the function under test resolves them
    monkeypatch.setattr(rs, "ConfigHelper", DummyConfigHelper)
    monkeypatch.setattr(rs, "BasicCLI", DummyCLI)
    monkeypatch.setattr(rs, "run_from_config", fake_run_from_config)

    # Ensure the module docstring check passes
    monkeypatch.setattr(rs, "__doc__", "module doc")

    # Ensure deterministic sys.argv for the branch where args is None
    old_argv = sys.argv
    try:
        sys.argv = ["program_name", "arg1", "arg2"]
        # call with args=None to take the branch at lines 210->211
        rs.run_from_cli(args=None)
    finally:
        sys.argv = old_argv

    assert "cfg" in captured, "run_from_config was not called"
    assert isinstance(captured["cfg"], dict)
    # ensure the CLI received sys.argv[1:]
    assert captured["cfg"]["args"] == ["arg1", "arg2"]


def test_explicit_args_preserved_round_128(monkeypatch):
    """When args is explicitly provided, run_from_cli must forward them unchanged
    and not read sys.argv.
    """
    captured = {}

    class DummyConfigHelper:
        def get_help(self, cfg):
            return "HELP"

    class DummyCLI:
        def __init__(self, cfg_cls, help_text=None):
            self.cfg_cls = cfg_cls
            self.help_text = help_text

        def get_config(self, args):
            return {"source": "DummyCLI.get_config", "args": list(args)}

    def fake_run_from_config(cfg):
        captured["cfg"] = cfg

    monkeypatch.setattr(rs, "ConfigHelper", DummyConfigHelper)
    monkeypatch.setattr(rs, "BasicCLI", DummyCLI)
    monkeypatch.setattr(rs, "run_from_config", fake_run_from_config)
    monkeypatch.setattr(rs, "__doc__", "docstring present")

    # Use a different sys.argv to ensure it would differ if read
    old_argv = sys.argv
    try:
        sys.argv = ["prog", "should", "not", "be", "used"]
        provided = ["explicit1", "explicit2"]
        rs.run_from_cli(args=provided)
    finally:
        sys.argv = old_argv

    assert "cfg" in captured
    assert captured["cfg"]["args"] == provided
