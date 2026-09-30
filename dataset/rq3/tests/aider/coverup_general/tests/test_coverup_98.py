# file: aider/main.py:1183-1223
# asked: {"lines": [1190, 1203, 1219, 1220, 1221, 1222, 1223], "branches": [[1189, 1190], [1202, 1203], [1221, 1222], [1221, 1223]]}
# gained: {"lines": [1190, 1203, 1219, 1220, 1221, 1222, 1223], "branches": [[1189, 1190], [1202, 1203], [1221, 1222]]}

import json
import sys
from pathlib import Path

import pytest

import aider.main as mainmod
from aider.main import is_first_run_of_new_version


class DummyIO:
    def __init__(self):
        self.outputs = []
        self.warnings = []

    def tool_output(self, msg):
        self.outputs.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)


def test_dev_version_returns_false(monkeypatch):
    # Ensure the function sees a ".dev" version and returns False immediately.
    monkeypatch.setattr(mainmod, "__version__", "9.9.9.dev0", raising=False)
    io = DummyIO()
    res = is_first_run_of_new_version(io, verbose=True)
    assert res is False
    # When .dev in version, function should return early and not log anything.
    assert io.outputs == []
    assert io.warnings == []


def test_installs_file_exists_verbose_reports_loaded(monkeypatch, tmp_path):
    # Redirect HOME so Path.home() points to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    # Pick a deterministic version and ensure mainmod uses it
    monkeypatch.setattr(mainmod, "__version__", "1.2.3", raising=False)

    # Prepare installs.json containing the key for current (__version__, sys.executable)
    installs_dir = tmp_path / ".aider"
    installs_dir.mkdir(parents=True, exist_ok=True)
    installs_file = installs_dir / "installs.json"
    key = (mainmod.__version__, sys.executable)
    installs = {str(key): True}
    installs_file.write_text(json.dumps(installs))

    io = DummyIO()
    res = is_first_run_of_new_version(io, verbose=True)
    # Key was present -> not first run
    assert res is False
    # verbose True should log that it checked and loaded the installs file (and show paths)
    # Ensure the specific "Installs file exists and loaded" message was emitted
    assert any("Installs file exists and loaded" in o for o in io.outputs)


def test_exception_path_returns_true_and_logs(monkeypatch):
    # Make Path.exists raise an exception to trigger the except branch
    def raises_exists(self):
        raise Exception("boom-exists")

    monkeypatch.setattr(Path, "exists", raises_exists, raising=True)

    io = DummyIO()
    # Ensure verbose True to also exercise the verbose exception output branch
    res = is_first_run_of_new_version(io, verbose=True)
    assert res is True
    # Confirm that a warning was emitted about the error
    assert any("Error checking version" in w for w in io.warnings)
    # Because verbose=True, the full exception details should also be output
    assert any("Full exception details:" in o for o in io.outputs)
