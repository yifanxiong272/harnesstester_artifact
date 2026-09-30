import types
import os
import pytest
from types import SimpleNamespace
from openhands.runtime.impl.cli import cli_runtime


class DummyLogger:
    def __init__(self):
        self.debug_messages = []
        self.error_messages = []

    def debug(self, msg):
        self.debug_messages.append(str(msg))

    def error(self, msg):
        self.error_messages.append(str(msg))


def make_self(runtime_initialized=True, sanitize_return=None):
    """Create a minimal self object compatible with CLIRuntime.copy_to."""
    s = SimpleNamespace()
    s._runtime_initialized = runtime_initialized
    if sanitize_return is None:
        sanitize_return = lambda v: v
    s._sanitize_filename = (lambda dest: sanitize_return) if not callable(sanitize_return) else sanitize_return
    return s


def test_copy_to_runtime_not_initialized_round_021():
    # If runtime not initialized, a RuntimeError is raised immediately.
    self = make_self(runtime_initialized=False, sanitize_return="/ignored")

    with pytest.raises(RuntimeError) as exc:
        cli_runtime.CLIRuntime.copy_to(self, "host_src", "dest", recursive=False)
    assert "Runtime not initialized" in str(exc.value)


def test_copy_to_source_missing_round_021(monkeypatch):
    # If the host source does not exist, FileNotFoundError is raised.
    logger = DummyLogger()
    monkeypatch.setattr(cli_runtime, "logger", logger)

    # Ensure runtime initialized, but host source not present
    self = make_self(runtime_initialized=True, sanitize_return="/dest")
    monkeypatch.setattr(cli_runtime.os.path, "exists", lambda p: False)

    with pytest.raises(FileNotFoundError) as exc:
        cli_runtime.CLIRuntime.copy_to(self, "/no/such/path", "dest", recursive=False)
    assert "Source path '/no/such/path' does not exist." in str(exc.value)
    # No error logs expected here because exception is raised before try/except
    assert logger.error_messages == []


def test_copy_to_dir_recursive_same_target_round_021(monkeypatch):
    # When copying a directory recursively and source == realpath(final_target_dir), skip copytree.
    logger = DummyLogger()
    monkeypatch.setattr(cli_runtime, "logger", logger)

    self = make_self(runtime_initialized=True, sanitize_return=lambda d: "/dest")
    host_src = "/some/dir"

    monkeypatch.setattr(cli_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, "isdir", lambda p: True if p == host_src else False)

    # final_target_dir will be os.path.join('/dest', os.path.basename(host_src)) => '/dest/dir'
    # Make realpath return same value for host_src and final_target_dir so copy is skipped.
    def fake_realpath(p):
        if p == host_src:
            return "/shared/real"
        return "/shared/real"

    monkeypatch.setattr(cli_runtime.os.path, "realpath", fake_realpath)

    # If copytree were called, it would indicate incorrect behavior. Patch to raise if invoked.
    def fake_copytree(src, dst, dirs_exist_ok=False):
        raise AssertionError("shutil.copytree should not be called when source and target are identical")

    monkeypatch.setattr(cli_runtime.shutil, "copytree", fake_copytree)

    # Should complete without error and not call copytree
    cli_runtime.CLIRuntime.copy_to(self, host_src, "dest", recursive=True)
    assert logger.debug_messages  # debug message about skipping should have been recorded
    assert any("Skipping recursive copy" in m for m in logger.debug_messages)


def test_copy_to_file_scenario_A_dir_dest_round_021(monkeypatch):
    # File source where sandbox_dest is a directory -> copy into that directory.
    logger = DummyLogger()
    monkeypatch.setattr(cli_runtime, "logger", logger)

    self = make_self(runtime_initialized=True, sanitize_return=lambda d: "/destdir")
    host_src = "/host/file.txt"

    monkeypatch.setattr(cli_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, "isdir", lambda p: False if p == host_src else True)
    monkeypatch.setattr(cli_runtime.os.path, "isfile", lambda p: True if p == host_src else False)

    makedirs_calls = []

    def fake_makedirs(path, exist_ok=False):
        makedirs_calls.append((path, exist_ok))

    monkeypatch.setattr(cli_runtime.os, "makedirs", fake_makedirs)

    copy2_calls = []

    def fake_copy2(src, dst):
        copy2_calls.append((src, dst))

    monkeypatch.setattr(cli_runtime.shutil, "copy2", fake_copy2)

    cli_runtime.CLIRuntime.copy_to(self, host_src, "dest/", recursive=False)

    assert copy2_calls == [(host_src, os.path.join("/destdir", os.path.basename(host_src)))]
    # Ensure we attempted to ensure existence of the directory
    assert any(c[0] == "/destdir" for c in makedirs_calls)


def test_copy_to_file_scenario_B_create_new_dir_round_021(monkeypatch):
    # File source where sandbox_dest is a name with no dot and does not exist -> create dir and copy.
    logger = DummyLogger()
    monkeypatch.setattr(cli_runtime, "logger", logger)

    # sanitize returns a path that does not exist and basename has no '.'
    self = make_self(runtime_initialized=True, sanitize_return=lambda d: "/new_dir")
    host_src = "/host/file.txt"

    monkeypatch.setattr(cli_runtime.os.path, "exists", lambda p: True if p == host_src else False)
    monkeypatch.setattr(cli_runtime.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(cli_runtime.os.path, "isfile", lambda p: True if p == host_src else False)

    makedirs_calls = []

    def fake_makedirs(path, exist_ok=False):
        makedirs_calls.append((path, exist_ok))

    monkeypatch.setattr(cli_runtime.os, "makedirs", fake_makedirs)

    copy2_calls = []

    def fake_copy2(src, dst):
        copy2_calls.append((src, dst))

    monkeypatch.setattr(cli_runtime.shutil, "copy2", fake_copy2)

    cli_runtime.CLIRuntime.copy_to(self, host_src, "new_dir", recursive=False)

    expected_target = os.path.join("/new_dir", os.path.basename(host_src))
    assert copy2_calls == [(host_src, expected_target)]
    assert any(c[0] == "/new_dir" for c in makedirs_calls)


def test_copy_to_file_scenario_C_samefileerror_round_021(monkeypatch):
    # If shutil.copy2 raises SameFileError, the method should swallow it (no exception).
    logger = DummyLogger()
    monkeypatch.setattr(cli_runtime, "logger", logger)

    self = make_self(runtime_initialized=True, sanitize_return=lambda d: "/dest/file.txt")
    host_src = "/host/file.txt"

    monkeypatch.setattr(cli_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(cli_runtime.os.path, "isfile", lambda p: True if p == host_src else False)

    # Prevent creation of real filesystem directories during test
    def fake_makedirs(path, exist_ok=False):
        return None

    monkeypatch.setattr(cli_runtime.os, "makedirs", fake_makedirs)

    def fake_copy2(src, dst):
        raise cli_runtime.shutil.SameFileError("same file")

    monkeypatch.setattr(cli_runtime.shutil, "copy2", fake_copy2)

    # Should not raise despite SameFileError
    cli_runtime.CLIRuntime.copy_to(self, host_src, "dest/file.txt", recursive=False)
    # debug message should be recorded for SameFileError handling
    assert any("Skipping copy as source and destination are the same" in m for m in logger.debug_messages)


def test_copy_to_unexpected_exception_round_021(monkeypatch):
    # If copy2 raises an unexpected Exception, it should be logged and re-raised as RuntimeError.
    logger = DummyLogger()
    monkeypatch.setattr(cli_runtime, "logger", logger)

    self = make_self(runtime_initialized=True, sanitize_return=lambda d: "/dest/file.txt")
    host_src = "/host/file.txt"

    monkeypatch.setattr(cli_runtime.os.path, "exists", lambda p: True)
    monkeypatch.setattr(cli_runtime.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(cli_runtime.os.path, "isfile", lambda p: True if p == host_src else False)

    # Prevent touching real filesystem
    monkeypatch.setattr(cli_runtime.os, "makedirs", lambda path, exist_ok=False: None)

    def fake_copy2(src, dst):
        raise Exception("boom")

    monkeypatch.setattr(cli_runtime.shutil, "copy2", fake_copy2)

    with pytest.raises(RuntimeError) as exc:
        cli_runtime.CLIRuntime.copy_to(self, host_src, "dest/file.txt", recursive=False)
    assert "Unexpected error copying file" in str(exc.value)
    assert any("Unexpected error copying file" in m for m in logger.error_messages)
