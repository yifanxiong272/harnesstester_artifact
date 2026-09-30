# file: openhands/runtime/action_execution_server.py:518-570
# asked: {"lines": [518, 519, 520, 521, 523, 524, 525, 527, 528, 529, 531, 533, 534, 535, 536, 537, 538, 540, 542, 543, 544, 546, 547, 548, 549, 550, 552, 553, 556, 557, 558, 560, 561, 564, 565, 566, 567, 568, 570], "branches": [[524, 525], [524, 527], [528, 529], [528, 531], [536, 537], [536, 540], [557, 558], [557, 564]]}
# gained: {"lines": [518, 519, 520, 521, 523, 524, 525, 527, 528, 529, 531, 533, 534, 535, 536, 537, 538, 540, 542, 543, 544, 546, 547, 548, 549, 550, 552, 553, 556, 557, 558, 560, 564, 565, 566, 567, 568, 570], "branches": [[524, 525], [524, 527], [528, 529], [528, 531], [536, 537], [536, 540], [557, 558], [557, 564]]}

import os
import builtins
from types import SimpleNamespace
import pytest

from openhands.runtime.action_execution_server import ActionExecutor
from openhands.events.observation import ErrorObservation, FileWriteObservation
from openhands.runtime.utils.files import insert_lines


@pytest.mark.asyncio
async def test_write_creates_new_file_and_returns_filewriteobservation(monkeypatch, tmp_path):
    # Prevent runtime init from trying to modify system users/sudoers
    monkeypatch.setattr('openhands.runtime.action_execution_server.init_user_and_working_directory', lambda *a, **k: None)

    # Arrange
    execr = ActionExecutor([], str(tmp_path), 'user', 1000, False, None)
    execr.bash_session = SimpleNamespace(cwd=str(tmp_path))

    # no-op chmod/chown to avoid PermissionError in test environment
    monkeypatch.setattr(os, "chmod", lambda *a, **k: None)
    monkeypatch.setattr(os, "chown", lambda *a, **k: None)

    action = SimpleNamespace(path="subdir/newfile.txt", content="line1\nline2", start=0, end=-1)
    filepath = os.path.join(str(tmp_path), "subdir", "newfile.txt")

    # Act
    obs = await execr.write(action)

    # Assert
    assert isinstance(obs, FileWriteObservation)
    assert obs.path == filepath
    # Ensure file was created and contains expected inserted lines
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    expected_lines = insert_lines(action.content.split("\n"), [], action.start, action.end)
    assert "".join(expected_lines) == content


@pytest.mark.asyncio
async def test_write_existing_file_unicode_decode_error(monkeypatch, tmp_path):
    # Prevent runtime init from trying to modify system users/sudoers
    monkeypatch.setattr('openhands.runtime.action_execution_server.init_user_and_working_directory', lambda *a, **k: None)

    # Arrange
    execr = ActionExecutor([], str(tmp_path), 'user', 1000, False, None)
    execr.bash_session = SimpleNamespace(cwd=str(tmp_path))

    # Create a file with invalid utf-8 bytes to trigger UnicodeDecodeError when read in text mode
    filepath = tmp_path / "badfile.txt"
    with open(filepath, "wb") as f:
        f.write(b"\xff\xff\xff")

    # no-op chmod/chown to avoid PermissionError in test environment
    monkeypatch.setattr(os, "chmod", lambda *a, **k: None)
    monkeypatch.setattr(os, "chown", lambda *a, **k: None)

    action = SimpleNamespace(path=str(filepath.name), content="newcontent", start=0, end=-1)

    # Act
    obs = await execr.write(action)

    # Assert
    assert isinstance(obs, ErrorObservation)
    assert "could not be decoded as utf-8" in obs.message


@pytest.mark.asyncio
async def test_write_path_is_directory_returns_error(monkeypatch, tmp_path):
    # Prevent runtime init from trying to modify system users/sudoers
    monkeypatch.setattr('openhands.runtime.action_execution_server.init_user_and_working_directory', lambda *a, **k: None)

    # Arrange
    execr = ActionExecutor([], str(tmp_path), 'user', 1000, False, None)
    execr.bash_session = SimpleNamespace(cwd=str(tmp_path))

    # Create a directory where the file is supposed to be
    target_dir = tmp_path / "mydir"
    target_dir.mkdir()
    action = SimpleNamespace(path=str(target_dir.name), content="irrelevant", start=0, end=-1)

    # Act
    obs = await execr.write(action)

    # Assert
    assert isinstance(obs, ErrorObservation)
    assert "Path is a directory" in obs.message


@pytest.mark.asyncio
async def test_write_open_raises_filenotfound_returns_error(monkeypatch, tmp_path):
    # Prevent runtime init from trying to modify system users/sudoers
    monkeypatch.setattr('openhands.runtime.action_execution_server.init_user_and_working_directory', lambda *a, **k: None)

    # Arrange
    execr = ActionExecutor([], str(tmp_path), 'user', 1000, False, None)
    execr.bash_session = SimpleNamespace(cwd=str(tmp_path))

    # Monkeypatch builtins.open to always raise FileNotFoundError during write
    def fake_open(*args, **kwargs):
        raise FileNotFoundError("no such file")
    monkeypatch.setattr(builtins, "open", fake_open)

    action = SimpleNamespace(path="somefile.txt", content="x", start=0, end=-1)

    # Act
    obs = await execr.write(action)

    # Assert
    assert isinstance(obs, ErrorObservation)
    assert "File not found" in obs.message


@pytest.mark.asyncio
async def test_write_chmod_chown_permissionerror_returns_error_existing_and_new(monkeypatch, tmp_path):
    # Prevent runtime init from trying to modify system users/sudoers
    monkeypatch.setattr('openhands.runtime.action_execution_server.init_user_and_working_directory', lambda *a, **k: None)

    # Test both existing and new file PermissionError during chmod/chown handling.

    # Existing file case
    execr1 = ActionExecutor([], str(tmp_path), 'user', 1000, False, None)
    execr1.bash_session = SimpleNamespace(cwd=str(tmp_path))

    existing = tmp_path / "exists.txt"
    existing.write_text("original\n", encoding="utf-8")

    # Make chmod raise PermissionError
    def raise_perm(*a, **k):
        raise PermissionError("no perms")
    monkeypatch.setattr(os, "chmod", raise_perm)
    # chown should not be reached but set to no-op
    monkeypatch.setattr(os, "chown", lambda *a, **k: None)

    action_existing = SimpleNamespace(path=str(existing.name), content="new", start=0, end=-1)
    obs1 = await execr1.write(action_existing)
    assert isinstance(obs1, ErrorObservation)
    assert "failed to change ownership and permissions" in obs1.message

    # New file case
    execr2 = ActionExecutor([], str(tmp_path), 'user', 1000, False, None)
    execr2.bash_session = SimpleNamespace(cwd=str(tmp_path))

    # Ensure chmod will raise for new file path as well
    monkeypatch.setattr(os, "chmod", raise_perm)
    monkeypatch.setattr(os, "chown", lambda *a, **k: None)

    new_path = "created_new.txt"
    action_new = SimpleNamespace(path=new_path, content="abc", start=0, end=-1)
    obs2 = await execr2.write(action_new)
    assert isinstance(obs2, ErrorObservation)
    assert "failed to change ownership and permissions" in obs2.message
