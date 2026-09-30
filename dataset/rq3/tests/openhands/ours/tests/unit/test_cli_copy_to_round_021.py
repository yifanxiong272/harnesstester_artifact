import builtins
import shutil
from types import SimpleNamespace
import pytest

from openhands.runtime.impl.cli import cli_runtime as cli_mod

# The tests below exercise CLIRuntime.copy_to branches by constructing a
# minimal `self` object with the attributes the method reads and by
# monkeypatching filesystem and shutil operations on the module under test.

def test_not_initialized_round_021():
    self = SimpleNamespace(_runtime_initialized=False)
    with pytest.raises(RuntimeError):
        cli_mod.CLIRuntime.copy_to(self, '/any', '/dest', recursive=False)


def test_source_missing_raises_FileNotFoundError_round_021(monkeypatch):
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: '/dest')

    # Source doesn't exist
    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: False)

    with pytest.raises(FileNotFoundError):
        cli_mod.CLIRuntime.copy_to(self, '/nope', '/dest', recursive=False)


def test_recursive_same_realpath_skips_copy_round_021(monkeypatch):
    host_src = '/host/dir'
    sandbox_dest = '/dest'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sandbox_dest)

    # Simulate source exists and is a directory
    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: p == host_src)

    # realpath returns identical values for source and the computed final target
    def fake_realpath(p):
        return '/SAME_REALPATH'
    monkeypatch.setattr(cli_mod.os.path, 'realpath', fake_realpath)

    called = {'makedirs': False, 'copytree': False}

    def fake_makedirs(path, exist_ok=False):
        called['makedirs'] = True
    def fake_copytree(src, dst, dirs_exist_ok=False):
        called['copytree'] = True

    monkeypatch.setattr(cli_mod.os, 'makedirs', fake_makedirs)
    monkeypatch.setattr(cli_mod.shutil, 'copytree', fake_copytree)

    # Should not raise and should *not* perform makedirs/copytree because realpaths match
    cli_mod.CLIRuntime.copy_to(self, host_src, '/ignored', recursive=True)
    assert called['makedirs'] is False
    assert called['copytree'] is False


def test_recursive_copytree_executes_and_makes_parent_round_021(monkeypatch):
    host_src = '/host/dir'
    sandbox_dest = '/dest'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sandbox_dest)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: p == host_src)

    # realpath differs for source and final target
    def fake_realpath(p):
        if p == host_src:
            return '/REAL_SRC'
        return '/REAL_DEST'
    monkeypatch.setattr(cli_mod.os.path, 'realpath', fake_realpath)

    records = {}

    def fake_makedirs(path, exist_ok=False):
        records['makedir'] = path

    def fake_copytree(src, dst, dirs_exist_ok=False):
        records['copytree'] = (src, dst, dirs_exist_ok)

    monkeypatch.setattr(cli_mod.os, 'makedirs', fake_makedirs)
    monkeypatch.setattr(cli_mod.shutil, 'copytree', fake_copytree)

    cli_mod.CLIRuntime.copy_to(self, host_src, sandbox_dest, recursive=True)

    assert records.get('makedir') == sandbox_dest
    # Expected final target directory is dest + basename(host_src)
    import os as _os
    expected_dst = _os.path.join(sandbox_dest, _os.path.basename(host_src))
    assert records.get('copytree') == (host_src, expected_dst, True)


def test_file_copy_into_existing_dir_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = '/destdir'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sandbox_dest)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True)
    # Source is file, destination is an existing directory
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: p == sandbox_dest)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)

    calls = {}

    def fake_makedirs(path, exist_ok=False):
        calls['makedirs'] = path

    def fake_copy2(src, dst):
        calls['copy2'] = (src, dst)

    monkeypatch.setattr(cli_mod.os, 'makedirs', fake_makedirs)
    monkeypatch.setattr(cli_mod.shutil, 'copy2', fake_copy2)

    cli_mod.CLIRuntime.copy_to(self, host_src, 'ignored', recursive=False)

    assert calls['makedirs'] == sandbox_dest
    assert calls['copy2'][0] == host_src
    assert calls['copy2'][1].endswith('/file.txt')


def test_file_copy_sandbox_with_trailing_slash_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = 'newdir/'
    sanitized = '/sanitized_newdir'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sanitized)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)
    # Destination is not an existing dir in os.path, but sandbox_dest endswith('/'), so chosen path should be sanitized
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: False)

    calls = {}
    monkeypatch.setattr(cli_mod.os, 'makedirs', lambda path, exist_ok=False: calls.setdefault('makedirs', path))
    monkeypatch.setattr(cli_mod.shutil, 'copy2', lambda src, dst: calls.setdefault('copy2', (src, dst)))

    cli_mod.CLIRuntime.copy_to(self, host_src, sandbox_dest, recursive=False)

    assert calls['makedirs'] == sanitized
    assert calls['copy2'][1].endswith('/file.txt')


def test_file_copy_new_dir_created_when_no_dot_in_basename_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = 'newdir'
    sanitized = '/newdir'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sanitized)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: False if p == sanitized else True)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: False)

    calls = {}
    monkeypatch.setattr(cli_mod.os, 'makedirs', lambda path, exist_ok=False: calls.setdefault('makedirs', path))
    monkeypatch.setattr(cli_mod.shutil, 'copy2', lambda src, dst: calls.setdefault('copy2', (src, dst)))

    cli_mod.CLIRuntime.copy_to(self, host_src, sandbox_dest, recursive=False)

    assert calls['makedirs'] == sanitized
    assert calls['copy2'][1].endswith('/file.txt')


def test_file_copy_else_full_file_path_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = 'some/path/target.txt'
    sanitized = '/some/path/target.txt'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sanitized)

    # dest does not exist but basename contains a dot -> else branch
    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: False)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: False)

    made = {}

    def fake_makedirs(path, exist_ok=False):
        made['parent'] = path

    def fake_copy2(src, dst):
        made['copy2'] = (src, dst)

    monkeypatch.setattr(cli_mod.os, 'makedirs', fake_makedirs)
    monkeypatch.setattr(cli_mod.shutil, 'copy2', fake_copy2)

    cli_mod.CLIRuntime.copy_to(self, host_src, sandbox_dest, recursive=False)

    # parent directory of the final target should be passed to makedirs
    assert made['parent'] == '/some/path'
    assert made['copy2'] == (host_src, sanitized)


def test_copy2_raises_FileNotFoundError_is_propagated_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = 'newdir'
    sanitized = '/newdir'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sanitized)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True if p == host_src else False)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: False)

    def raise_fn(src, dst):
        raise FileNotFoundError('during copy2')

    monkeypatch.setattr(cli_mod.os, 'makedirs', lambda path, exist_ok=False: None)
    monkeypatch.setattr(cli_mod.shutil, 'copy2', raise_fn)

    with pytest.raises(FileNotFoundError):
        cli_mod.CLIRuntime.copy_to(self, host_src, sandbox_dest, recursive=False)


def test_copy2_raises_SameFileError_is_ignored_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = '/dest'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sandbox_dest)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: False)

    def raise_samefile(src, dst):
        raise shutil.SameFileError('same file')

    monkeypatch.setattr(cli_mod.os, 'makedirs', lambda path, exist_ok=False: None)
    monkeypatch.setattr(cli_mod.shutil, 'copy2', raise_samefile)

    # Should not raise because SameFileError is caught and passed
    cli_mod.CLIRuntime.copy_to(self, host_src, 'ignored', recursive=False)


def test_copy2_raises_generic_exception_becomes_RuntimeError_round_021(monkeypatch):
    host_src = '/path/file.txt'
    sandbox_dest = '/dest'
    self = SimpleNamespace(_runtime_initialized=True, _sanitize_filename=lambda s: sandbox_dest)

    monkeypatch.setattr(cli_mod.os.path, 'exists', lambda p: True)
    monkeypatch.setattr(cli_mod.os.path, 'isfile', lambda p: p == host_src)
    monkeypatch.setattr(cli_mod.os.path, 'isdir', lambda p: False)

    def raise_value_error(src, dst):
        raise ValueError('boom')

    monkeypatch.setattr(cli_mod.os, 'makedirs', lambda path, exist_ok=False: None)
    monkeypatch.setattr(cli_mod.shutil, 'copy2', raise_value_error)

    with pytest.raises(RuntimeError) as excinfo:
        cli_mod.CLIRuntime.copy_to(self, host_src, 'ignored', recursive=False)
    assert 'Unexpected error copying file' in str(excinfo.value)
