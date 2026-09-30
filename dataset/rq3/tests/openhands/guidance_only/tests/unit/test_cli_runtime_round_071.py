import builtins
import io
import types
import pytest
from types import SimpleNamespace

from openhands.runtime.impl.cli import cli_runtime
from openhands.runtime.impl.cli.cli_runtime import CLIRuntime, FileReadObservation, ErrorObservation, FileReadSource


# Helper to create a CLIRuntime instance without running __init__
def _make_runtime():
    rt = object.__new__(CLIRuntime)
    # default sanitizer to identity unless tests override
    rt._sanitize_filename = lambda p: p
    return rt


def test_read_not_initialized_round_071():
    """When runtime not initialized, read should return a Runtime not initialized ErrorObservation."""
    runtime = _make_runtime()
    runtime._runtime_initialized = False
    action = SimpleNamespace(path="/some/path.txt", impl_source=None, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    # Construct expected ErrorObservation and assert equality
    assert isinstance(obs, ErrorObservation)
    assert obs == ErrorObservation('Runtime not initialized')


def test_read_oh_aci_uses_editor_round_071(monkeypatch):
    """When impl_source is OH_ACI, the editor is invoked and its result is returned as FileReadObservation."""
    runtime = _make_runtime()
    runtime._runtime_initialized = True

    # sanitize returns a path (unused by mocked editor but kept realistic)
    runtime._sanitize_filename = lambda p: "/sanitized/path.py"

    # patch the instance method _execute_file_editor to simulate OHEditor behavior
    def fake_execute(command, path, view_range=None):
        assert command == 'view'
        assert path == "/sanitized/path.py"
        return ("editor content", None)

    monkeypatch.setattr(runtime, '_execute_file_editor', fake_execute)

    action = SimpleNamespace(path="orig/path.py", impl_source=FileReadSource.OH_ACI, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    assert isinstance(obs, FileReadObservation)
    assert obs.content == "editor content"
    assert obs.path == "orig/path.py"
    assert obs.impl_source == FileReadSource.OH_ACI


def test_read_file_not_found_round_071(monkeypatch):
    """If the sanitized filename does not exist, return a File not found ErrorObservation."""
    runtime = _make_runtime()
    runtime._runtime_initialized = True

    runtime._sanitize_filename = lambda p: "/not/exist.txt"

    # patch os.path.exists to always return False for this path
    monkeypatch.setattr(cli_runtime.os.path, 'exists', lambda p: False)

    action = SimpleNamespace(path="nope.txt", impl_source=None, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    assert isinstance(obs, ErrorObservation)
    assert obs == ErrorObservation(f'File not found: {action.path}')


def test_read_directory_round_071(monkeypatch):
    """When path exists but is a directory, return Cannot read directory ErrorObservation."""
    runtime = _make_runtime()
    runtime._runtime_initialized = True

    runtime._sanitize_filename = lambda p: "/some/dir"

    monkeypatch.setattr(cli_runtime.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, 'isdir', lambda p: True)

    action = SimpleNamespace(path="a_dir", impl_source=None, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    assert isinstance(obs, ErrorObservation)
    assert obs == ErrorObservation(f'Cannot read directory: {action.path}')


def test_read_binary_file_round_071(monkeypatch):
    """If file is binary, read should return the ERROR_BINARY_FILE ErrorObservation."""
    runtime = _make_runtime()
    runtime._runtime_initialized = True

    runtime._sanitize_filename = lambda p: "/some/file.bin"

    monkeypatch.setattr(cli_runtime.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(cli_runtime, 'is_binary', lambda p: True)

    action = SimpleNamespace(path="file.bin", impl_source=None, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    assert isinstance(obs, ErrorObservation)
    assert obs == ErrorObservation('ERROR_BINARY_FILE')


def test_read_successful_text_file_round_071(monkeypatch):
    """When file exists and is text, content is read and returned in FileReadObservation."""
    runtime = _make_runtime()
    runtime._runtime_initialized = True

    runtime._sanitize_filename = lambda p: "/some/text.txt"

    monkeypatch.setattr(cli_runtime.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(cli_runtime, 'is_binary', lambda p: False)

    # patch builtins.open to return a StringIO when called
    def fake_open(path, mode='r', encoding=None, errors=None):
        assert path == "/some/text.txt"
        return io.StringIO("hello world")

    monkeypatch.setattr(builtins, 'open', fake_open)

    action = SimpleNamespace(path="text.txt", impl_source=None, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    assert isinstance(obs, FileReadObservation)
    assert obs.content == "hello world"
    assert obs.path == "text.txt"


def test_read_raises_and_returns_error_round_071(monkeypatch):
    """If reading the file raises, CLIRuntime.read should catch and return an ErrorObservation with the exception message."""
    runtime = _make_runtime()
    runtime._runtime_initialized = True

    runtime._sanitize_filename = lambda p: "/some/fail.txt"

    monkeypatch.setattr(cli_runtime.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, 'isdir', lambda p: False)
    monkeypatch.setattr(cli_runtime, 'is_binary', lambda p: False)

    def raising_open(*args, **kwargs):
        raise Exception('boom')

    monkeypatch.setattr(builtins, 'open', raising_open)

    action = SimpleNamespace(path="fail.txt", impl_source=None, view_range=None)

    obs = CLIRuntime.read(runtime, action)

    assert isinstance(obs, ErrorObservation)
    assert obs == ErrorObservation(f'Error reading file {action.path}: boom')
