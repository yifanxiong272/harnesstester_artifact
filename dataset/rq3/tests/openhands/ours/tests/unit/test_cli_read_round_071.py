import builtins
import types
from pathlib import Path
import os
import io
import pytest

from openhands.runtime.impl.cli.cli_runtime import (
    CLIRuntime,
    FileReadSource,
)
from openhands.events.observation import ErrorObservation, FileReadObservation


def _text_of_observation(obs):
    """Try to extract a human-readable message/content from various observation shapes.
    This avoids depending on a specific attribute name on ErrorObservation implementations.
    """
    # Common field names we might expect
    for name in ("message", "error", "detail", "content", "path"):
        if hasattr(obs, name):
            val = getattr(obs, name)
            if isinstance(val, str):
                return val
            try:
                return str(val)
            except Exception:
                pass
    # Fallback to stringification
    return str(obs)


def _make_runtime():
    # Bypass constructor to create a light-weight CLIRuntime instance we can control
    rt = CLIRuntime.__new__(CLIRuntime)
    # Default behavior: runtime initialized
    rt._runtime_initialized = True
    # Default sanitizer: return same string path
    rt._sanitize_filename = lambda filename: str(filename)
    # Default editor: raise if used unless test sets it
    rt._execute_file_editor = lambda **kwargs: ("", None)
    return rt


def test_read_not_initialized_round_071():
    rt = _make_runtime()
    rt._runtime_initialized = False
    action = types.SimpleNamespace(path="/no/matter.txt", impl_source=None, view_range=None)

    obs = rt.read(action)

    assert isinstance(obs, ErrorObservation)
    assert "Runtime not initialized" in _text_of_observation(obs)


def test_read_oh_aci_uses_editor_round_071():
    rt = _make_runtime()
    # ensure runtime is initialized
    rt._runtime_initialized = True

    # make the editor return predictable content
    def fake_editor(command, path, view_range=None, **kwargs):
        # verify the contract (we expect the call shape used in read)
        assert command == "view"
        assert isinstance(path, str)
        return ("EDITOR_CONTENT_LINE", None)

    rt._execute_file_editor = fake_editor

    action = types.SimpleNamespace(path="/some/aci/file.aci", impl_source=FileReadSource.OH_ACI, view_range=(1, 10))

    obs = rt.read(action)

    # Should return a FileReadObservation populated with the editor content and original path
    assert isinstance(obs, FileReadObservation)
    assert getattr(obs, "content", None) == "EDITOR_CONTENT_LINE"
    # path returned should be the original action.path
    assert getattr(obs, "path", None) == action.path
    # Also verify the observation notes the OH_ACI source when available
    # Do a relaxed check in case the field name differs; string should contain the path or content
    assert action.path in _text_of_observation(obs) or "EDITOR_CONTENT_LINE" in _text_of_observation(obs)


def test_read_file_not_found_round_071(tmp_path):
    rt = _make_runtime()
    rt._runtime_initialized = True

    missing = tmp_path / "does_not_exist.txt"
    action = types.SimpleNamespace(path=str(missing), impl_source=None, view_range=None)

    obs = rt.read(action)

    assert isinstance(obs, ErrorObservation)
    assert f"File not found: {action.path}" in _text_of_observation(obs)


def test_read_directory_round_071(tmp_path):
    rt = _make_runtime()
    rt._runtime_initialized = True

    dirpath = tmp_path / "somedir"
    dirpath.mkdir()

    action = types.SimpleNamespace(path=str(dirpath), impl_source=None, view_range=None)

    obs = rt.read(action)

    assert isinstance(obs, ErrorObservation)
    assert f"Cannot read directory: {action.path}" in _text_of_observation(obs)


def test_read_binary_file_round_071(tmp_path, monkeypatch):
    rt = _make_runtime()
    rt._runtime_initialized = True

    filepath = tmp_path / "binary.bin"
    filepath.write_bytes(b"\x00\x01\x02")
    action = types.SimpleNamespace(path=str(filepath), impl_source=None, view_range=None)

    # Patch the is_binary function in the module so the code under test sees the file as binary
    import openhands.runtime.impl.cli.cli_runtime as cli_mod

    monkeypatch.setattr(cli_mod, "is_binary", lambda p: True)

    obs = rt.read(action)

    assert isinstance(obs, ErrorObservation)
    assert "ERROR_BINARY_FILE" in _text_of_observation(obs)


def test_read_text_file_success_round_071(tmp_path, monkeypatch):
    rt = _make_runtime()
    rt._runtime_initialized = True

    text = "hello world\nsecond line"
    filepath = tmp_path / "note.txt"
    filepath.write_text(text, encoding="utf-8")

    action = types.SimpleNamespace(path=str(filepath), impl_source=None, view_range=None)

    # Ensure binary check returns False for this file
    import openhands.runtime.impl.cli.cli_runtime as cli_mod

    monkeypatch.setattr(cli_mod, "is_binary", lambda p: False)

    obs = rt.read(action)

    assert isinstance(obs, FileReadObservation)
    assert getattr(obs, "content", None) == text
    assert getattr(obs, "path", None) == action.path


def test_read_open_exception_round_071(tmp_path, monkeypatch):
    rt = _make_runtime()
    rt._runtime_initialized = True

    filepath = tmp_path / "will_fail.txt"
    filepath.write_text("data")
    action = types.SimpleNamespace(path=str(filepath), impl_source=None, view_range=None)

    # Make is_binary return False so we reach the open() call
    import openhands.runtime.impl.cli.cli_runtime as cli_mod
    monkeypatch.setattr(cli_mod, "is_binary", lambda p: False)

    # Replace builtins.open with a function that raises when attempting to open our target
    real_open = builtins.open

    def fake_open(file, mode="r", encoding=None, errors=None):
        if str(file) == str(filepath):
            raise IOError("simulated read failure")
        return real_open(file, mode, encoding=encoding, errors=errors)

    monkeypatch.setattr(builtins, "open", fake_open)

    obs = rt.read(action)

    assert isinstance(obs, ErrorObservation)
    # Should mention the action path and the simulated error
    text = _text_of_observation(obs)
    assert "Error reading file" in text
    assert action.path in text
