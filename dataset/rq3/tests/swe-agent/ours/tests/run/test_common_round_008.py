import types
import pytest
from pathlib import Path
import importlib

import sweagent.run.common as common

# Test 1: When --help is provided and BasicCLI.help_text is set,
# the code should call rich_print with the help text and then exit (SystemExit).
def test_help_text_shown_round_008(monkeypatch):
    # Create a BasicCLI with an explicit help_text
    cli = common.BasicCLI(config_type=object, default_settings=False, help_text="HELPTEXT")

    printed = []
    # Patch rich_print used inside the function to capture the printed text instead of printing to stdout
    monkeypatch.setattr(common, "rich_print", lambda x: printed.append(x))

    with pytest.raises(SystemExit):
        cli.get_config(["--help"])

    # The help_text should have been passed to rich_print exactly once
    assert printed == ["HELPTEXT"]


# Test 2: When a user supplies --config pointing to a file that is empty,
# the code should call logger.warning for that file and still return some config object
# (CliApp.run is stubbed to return a simple object). This covers the branch for empty config files.
def test_config_file_empty_flag_round_008(monkeypatch):
    # Stub Path.read_text used by the module so we don't touch the real filesystem.
    def fake_read_text(self):
        # Return whitespace-only content for a file named 'some.yaml' to trigger the "empty file" branch
        if self.name == "some.yaml":
            return "   \n"
        # Any other file -> non-empty
        return "{\"k\": \"v\"}"

    monkeypatch.setattr(common.Path, "read_text", fake_read_text, raising=False)

    # Stub CliApp.run to return a simple object instead of invoking pydantic/pydantic-settings
    monkeypatch.setattr(common.CliApp, "run", lambda *a, **kw: types.SimpleNamespace(), raising=False)

    # Instantiate CLI without default settings so the --config branch is taken
    cli = common.BasicCLI(config_type=object, default_settings=False, help_text=None)

    # Replace the logger on the instance so we can capture warnings deterministically
    captured_warnings = []
    cli.logger = types.SimpleNamespace(warning=lambda msg: captured_warnings.append(msg), info=lambda msg: None)

    # Call with a --config pointing to 'some.yaml'
    cfg = cli.get_config(["--config", "some.yaml"])

    # The returned config should be the object returned by our stub
    assert isinstance(cfg, types.SimpleNamespace)

    # The CLI should have attached the list of config files (Path objects)
    assert getattr(cfg, "_config_files") == [Path("some.yaml")]

    # We should have observed at least one warning about the empty config file
    assert any("Config file" in str(m) for m in captured_warnings), captured_warnings


# Test 3: When default settings are enabled and the default config file is empty,
# and CliApp.run raises a ValidationError, the function should print diagnostics and then raise a RuntimeError.
def test_default_file_empty_and_validation_error_round_008(monkeypatch):
    # Make Path.read_text return empty string for default.yaml to trigger the "default file is empty" branch
    def fake_read_text(self):
        if self.name == "default.yaml":
            return ""
        return "{}"

    monkeypatch.setattr(common.Path, "read_text", fake_read_text, raising=False)

    # Replace the ValidationError symbol in the module with a simple custom exception class
    CustomValError = type("CustomValError", (Exception,), {})
    monkeypatch.setattr(common, "ValidationError", CustomValError)

    # Make CliApp.run raise our substituted ValidationError to drive the exception-handling branch
    def raise_validation(*args, **kwargs):
        raise CustomValError("validation failed")

    monkeypatch.setattr(common.CliApp, "run", raise_validation, raising=False)

    # Patch rich_print used during error handling so it doesn't produce noisy output during tests
    monkeypatch.setattr(common, "rich_print", lambda *a, **kw: None)

    # Instantiate CLI with default_settings True so the default file path branch is taken
    cli = common.BasicCLI(config_type=object, default_settings=True, help_text=None)

    # Capture whether maybe_show_auto_correct is called; replace it with a deterministic spy
    called = {"auto_correct": False}

    def spy_maybe_show_auto_correct(args):
        called["auto_correct"] = True

    cli.maybe_show_auto_correct = spy_maybe_show_auto_correct

    # Replace logger to capture warnings about the default file being empty
    captured = []
    cli.logger = types.SimpleNamespace(warning=lambda msg: captured.append(msg), info=lambda msg: None)

    # When the ValidationError occurs, the code should end up raising a RuntimeError with a specific message
    with pytest.raises(RuntimeError) as excinfo:
        cli.get_config([])

    assert str(excinfo.value) == "Invalid configuration. Please check the above output."

    # The default file empty branch should have produced a warning
    assert any("default" in str(m).lower() or "default" in str(m) for m in captured), captured

    # maybe_show_auto_correct should have been called during error handling
    assert called["auto_correct"] is True
