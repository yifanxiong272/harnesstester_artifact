import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import aider.main as main


class FakeIO:
    def __init__(self):
        self.outputs = []
        self.warnings = []

    def tool_output(self, msg):
        self.outputs.append(str(msg))

    def tool_warning(self, msg):
        self.warnings.append(str(msg))


def test_dev_version_returns_false_round_163(tmp_path):
    """When __version__ contains .dev the function should return False immediately."""
    fake_io = FakeIO()

    # Ensure Path.home points to an isolated temp directory (not strictly needed for dev path,
    # but keeps tests hermetic).
    with patch.object(main.Path, "home", return_value=tmp_path):
        with patch.object(main, "__version__", "9.9.9.dev"):
            result = main.is_first_run_of_new_version(fake_io, verbose=False)

    assert result is False
    # No outputs or warnings should have been produced for the early return
    assert fake_io.outputs == []
    assert fake_io.warnings == []


def test_installs_file_exists_and_verbose_outputs_round_163(tmp_path):
    """When an installs file exists and verbose=True, an informative tool_output should be emitted
    and the installs.json should be updated for a first run key.
    """
    fake_io = FakeIO()

    # Prepare a fake home with a pre-existing .aider/installs.json
    home = tmp_path
    aider_dir = home / ".aider"
    aider_dir.mkdir(parents=True)
    installs_file = aider_dir / "installs.json"
    # Start with an empty installs dict so key will not be present and is_first_run -> True
    installs_file.write_text(json.dumps({}))

    version_value = "1.2.3"

    with patch.object(main.Path, "home", return_value=home):
        with patch.object(main, "__version__", version_value):
            result = main.is_first_run_of_new_version(fake_io, verbose=True)

    # Because the key wasn't present in the file, this should report first-run True
    assert result is True

    # The verbose message indicating the installs file was loaded should be present
    assert any("Installs file exists and loaded" in o for o in fake_io.outputs), (
        "Expected verbose output about loaded installs file")

    # The installs.json should now contain the key for this (version, executable)
    with open(installs_file, "r") as f:
        installs_after = json.load(f)

    expected_key = str((version_value, sys.executable))
    assert expected_key in installs_after


def test_exception_logs_and_returns_true_verbose_round_163(tmp_path):
    """If an exception occurs while checking/loading the installs file, the function should
    emit a tool_warning, optionally emit full exception details when verbose=True, and
    return True.
    We provoke an exception by patching Path.exists to raise.
    """
    fake_io = FakeIO()

    with patch.object(main.Path, "home", return_value=tmp_path):
        # Cause any call to Path.exists() to raise an exception, triggering the except branch
        with patch.object(main.Path, "exists", side_effect=RuntimeError("boom")):
            with patch.object(main, "__version__", "2.0.0"):
                result = main.is_first_run_of_new_version(fake_io, verbose=True)

    # On exception, function should return True (safer to assume first run)
    assert result is True

    # A warning about the error should have been emitted
    assert any("Error checking version:" in w for w in fake_io.warnings), (
        "Expected a tool_warning about the error")

    # With verbose=True, full exception details should be output
    assert any("Full exception details:" in o for o in fake_io.outputs), (
        "Expected verbose full exception details in tool_output")
