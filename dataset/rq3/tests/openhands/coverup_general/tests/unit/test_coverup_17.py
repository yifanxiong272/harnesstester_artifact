# file: openhands/runtime/utils/runtime_init.py:15-134
# asked: {"lines": [15, 16, 17, 44, 45, 46, 49, 50, 52, 56, 57, 60, 61, 63, 64, 65, 66, 67, 69, 72, 73, 74, 77, 78, 80, 81, 83, 84, 85, 88, 89, 91, 93, 95, 96, 97, 98, 99, 100, 103, 104, 105, 107, 108, 109, 110, 113, 114, 118, 119, 120, 121, 124, 125, 126, 127, 129, 130, 131, 132, 134], "branches": [[44, 45], [44, 56], [56, 57], [56, 60], [61, 63], [61, 118], [72, 73], [72, 77], [83, 84], [83, 88], [93, 95], [93, 118], [97, 98], [97, 99], [108, 109], [108, 113]]}
# gained: {"lines": [15, 17, 44, 45, 46, 49, 50, 52, 56, 57, 60, 61, 63, 64, 65, 66, 67, 69, 72, 73, 74, 77, 78, 80, 81, 83, 84, 85, 88, 89, 91, 93, 95, 96, 97, 98, 99, 100, 103, 104, 105, 107, 108, 109, 110, 113, 114, 118, 119, 120, 121, 124, 125, 126, 127, 129, 130, 131, 132, 134], "branches": [[44, 45], [44, 56], [56, 57], [56, 60], [61, 63], [72, 73], [72, 77], [83, 84], [83, 88], [93, 95], [93, 118], [97, 98], [97, 99], [108, 109], [108, 113]]}

import subprocess
import sys
from types import SimpleNamespace

import pytest

import openhands.runtime.utils.runtime_init as runtime_init


def _make_namespace(stdout=b"", stderr=b"", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_windows_branch(tmp_path, monkeypatch):
    # Simulate Windows platform
    monkeypatch.setattr(sys, "platform", "win32")
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("subprocess.run should not be called on Windows branch")

    # Patch subprocess.run in the module to detect unwanted calls; include CalledProcessError
    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    initial_cwd = tmp_path / "workdir_win"
    # Ensure it does not exist before
    assert not initial_cwd.exists()

    result = runtime_init.init_user_and_working_directory("anyuser", 1000, str(initial_cwd))
    # On Windows branch, the function returns None and creates the directory via os.makedirs
    assert result is None
    assert initial_cwd.exists() and initial_cwd.is_dir()


def test_skip_current_user(monkeypatch):
    # If username equals $USER and not root/openhands, function should return None immediately
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("USER", "current_user")
    called = {"run": False}

    def fake_run(*args, **kwargs):
        called["run"] = True
        return _make_namespace()

    # ensure CalledProcessError present though it won't be used
    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    res = runtime_init.init_user_and_working_directory("current_user", 1000, "/tmp/should_not_create")
    assert res is None
    assert not called["run"]  # subprocess.run shouldn't be called


def test_user_exists_same_uid(monkeypatch, tmp_path):
    # id -u returns same UID -> should skip setup_user and return existing UID
    monkeypatch.setattr(sys, "platform", "linux")
    username = "bob"
    user_id = 1000
    initial_cwd = tmp_path / "cwd_same_uid"

    calls = []

    def fake_run(cmd, shell=True, check=False, capture_output=True):
        calls.append(cmd)
        # id -u call uses check=True
        if cmd.startswith(f"id -u {username}"):
            return _make_namespace(stdout=str(user_id).encode(), returncode=0)
        # mkdir/chown/chmod commands
        if cmd.startswith("umask"):
            return _make_namespace(stdout=b"made_dir", returncode=0)
        if cmd.startswith("chown"):
            return _make_namespace(stdout=b"chowned", returncode=0)
        if cmd.startswith("chmod"):
            return _make_namespace(stdout=b"chmodded", returncode=0)
        return _make_namespace()

    # Patch subprocess.run in the module and provide CalledProcessError
    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )

    res = runtime_init.init_user_and_working_directory(username, user_id, str(initial_cwd))
    assert res == user_id
    # Ensure id -u was called and final commands were invoked
    assert any(cmd.startswith(f"id -u {username}") for cmd in calls)
    assert any(cmd.startswith("umask 002; mkdir -p") for cmd in calls)
    assert any(cmd.startswith(f"chown -R {username}:") for cmd in calls)
    assert any(cmd.startswith("chmod g+rw") for cmd in calls)


def test_user_exists_different_uid(monkeypatch, tmp_path):
    # id -u returns different UID -> should log warning and return that UID
    monkeypatch.setattr(sys, "platform", "linux")
    username = "charlie"
    existing_uid = 2000
    initial_cwd = tmp_path / "cwd_diff_uid"

    def fake_run(cmd, shell=True, check=False, capture_output=True):
        if cmd.startswith(f"id -u {username}"):
            return _make_namespace(stdout=str(existing_uid).encode(), returncode=0)
        # other commands
        return _make_namespace()

    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    res = runtime_init.init_user_and_working_directory(username, 1000, str(initial_cwd))
    assert res == existing_uid


def test_user_does_not_exist_and_useradd_success(monkeypatch, tmp_path):
    # id -u raises CalledProcessError with returncode 1 -> proceed to create user
    monkeypatch.setattr(sys, "platform", "linux")
    username = "newuser"
    user_id = 1500
    initial_cwd = tmp_path / "cwd_new_user"
    calls = []

    def fake_run(cmd, shell=True, check=False, capture_output=True):
        calls.append(cmd)
        if isinstance(cmd, str) and cmd.startswith(f"id -u {username}"):
            # Simulate non-existing user by raising the original subprocess.CalledProcessError
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, output=b"", stderr=b"user not found")
        if isinstance(cmd, str) and cmd.startswith("echo '%sudo"):
            return _make_namespace(stdout=b"succeed", returncode=0)
        if isinstance(cmd, str) and cmd.startswith("useradd"):
            return _make_namespace(stdout=b"useradd ok", returncode=0)
        if isinstance(cmd, str) and cmd.startswith("umask"):
            return _make_namespace(stdout=b"mkdir ok", returncode=0)
        if isinstance(cmd, str) and cmd.startswith("chown"):
            return _make_namespace(stdout=b"chown ok", returncode=0)
        if isinstance(cmd, str) and cmd.startswith("chmod"):
            return _make_namespace(stdout=b"chmod ok", returncode=0)
        return _make_namespace()

    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    res = runtime_init.init_user_and_working_directory(username, user_id, str(initial_cwd))
    # existing_user_id remains -1 so function returns None
    assert res is None
    # Ensure user creation commands ran
    assert any(isinstance(cmd, str) and cmd.startswith("echo '%sudo") for cmd in calls)
    assert any(isinstance(cmd, str) and cmd.startswith("useradd") for cmd in calls)
    assert any(isinstance(cmd, str) and cmd.startswith("umask 002; mkdir -p") for cmd in calls)


def test_user_check_error_raises(monkeypatch):
    # id -u raises CalledProcessError with returncode != 1 -> function should re-raise
    monkeypatch.setattr(sys, "platform", "linux")
    username = "badcheck"

    def fake_run(cmd, shell=True, check=False, capture_output=True):
        if isinstance(cmd, str) and cmd.startswith(f"id -u {username}"):
            raise subprocess.CalledProcessError(returncode=2, cmd=cmd, output=b"", stderr=b"other error")
        return _make_namespace()

    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    with pytest.raises(subprocess.CalledProcessError):
        runtime_init.init_user_and_working_directory(username, 1234, "/tmp/irrelevant")


def test_sudoer_add_fail_raises(monkeypatch):
    # id -u indicates user does not exist -> sudoer addition returns non-zero -> RuntimeError
    monkeypatch.setattr(sys, "platform", "linux")
    username = "sudofail"

    def fake_run(cmd, shell=True, check=False, capture_output=True):
        if isinstance(cmd, str) and cmd.startswith(f"id -u {username}"):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, output=b"", stderr=b"no user")
        if isinstance(cmd, str) and cmd.startswith("echo '%sudo"):
            return _make_namespace(stdout=b"", stderr=b"denied", returncode=1)
        return _make_namespace()

    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    with pytest.raises(RuntimeError):
        runtime_init.init_user_and_working_directory(username, 3000, "/tmp/irrelevant2")


def test_useradd_fail_raises(monkeypatch):
    # id -u indicates user does not exist -> sudoer ok -> useradd fails -> RuntimeError
    monkeypatch.setattr(sys, "platform", "linux")
    username = "useraddfail"

    def fake_run(cmd, shell=True, check=False, capture_output=True):
        if isinstance(cmd, str) and cmd.startswith(f"id -u {username}"):
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, output=b"", stderr=b"no user")
        if isinstance(cmd, str) and cmd.startswith("echo '%sudo"):
            return _make_namespace(stdout=b"", stderr=b"", returncode=0)
        if isinstance(cmd, str) and cmd.startswith("useradd"):
            return _make_namespace(stdout=b"", stderr=b"useradd error", returncode=1)
        return _make_namespace()

    monkeypatch.setattr(
        runtime_init,
        "subprocess",
        SimpleNamespace(run=fake_run, CalledProcessError=subprocess.CalledProcessError),
    )
    with pytest.raises(RuntimeError):
        runtime_init.init_user_and_working_directory(username, 4000, "/tmp/irrelevant3")
