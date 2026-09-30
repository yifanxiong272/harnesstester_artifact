import os
import time
import tempfile
from pathlib import Path
import pytest

from openhands.runtime.utils.port_lock import cleanup_stale_locks


def test_cleanup_no_dir_round_057(tmp_path, monkeypatch):
    """If the lock directory doesn't exist, cleanup_stale_locks should return 0."""
    # Point tempfile.gettempdir() to a directory that does not contain the locks dir
    fake_temp = tmp_path / "some_temp"
    # ensure it exists but doesn't contain 'openhands_port_locks'
    fake_temp.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fake_temp))

    cleaned = cleanup_stale_locks(max_age_seconds=10)
    assert cleaned == 0


def test_cleanup_with_stale_and_fresh_files_round_057(tmp_path, monkeypatch):
    """Create one stale and one fresh 'port_*.lock' file. Only the stale one should be removed."""
    base = tmp_path
    lock_dir = base / "openhands_port_locks"
    lock_dir.mkdir()

    stale = lock_dir / "port_111.lock"
    fresh = lock_dir / "port_222.lock"
    other = lock_dir / "not_a_lock.txt"

    stale.write_text("stale")
    fresh.write_text("fresh")
    other.write_text("other")

    now = time.time()
    # Make stale older than max_age_seconds (set to 5 below)
    os.utime(stale, (now - 1000, now - 1000))
    # Fresh has current mtime
    os.utime(fresh, (now, now))

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(base))

    cleaned = cleanup_stale_locks(max_age_seconds=5)
    assert cleaned == 1

    # stale should have been removed, fresh and other remain
    assert not stale.exists()
    assert fresh.exists()
    assert other.exists()


def test_cleanup_unlink_raises_round_057(tmp_path, monkeypatch):
    """If os.unlink raises OSError while removing a stale lock, cleaned should not increment and the file remains."""
    base = tmp_path
    lock_dir = base / "openhands_port_locks"
    lock_dir.mkdir()

    f = lock_dir / "port_333.lock"
    f.write_text("data")

    now = time.time()
    os.utime(f, (now - 1000, now - 1000))

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(base))

    # Patch os.unlink to raise OSError to simulate a failure while removing
    def raise_on_unlink(path):
        raise OSError("simulated unlink failure")

    monkeypatch.setattr(os, "unlink", raise_on_unlink)

    cleaned = cleanup_stale_locks(max_age_seconds=5)

    # Because unlink failed, cleaned should remain 0 and file should still exist
    assert cleaned == 0
    assert f.exists()


def test_cleanup_listdir_raises_round_057(tmp_path, monkeypatch):
    """If os.listdir raises OSError, the function should handle it and return 0."""
    base = tmp_path
    lock_dir = base / "openhands_port_locks"
    lock_dir.mkdir()

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(base))

    # Make os.listdir raise OSError when called for the locks dir
    def listdir_raises(path):
        raise OSError("simulated listdir failure")

    monkeypatch.setattr(os, "listdir", listdir_raises)

    cleaned = cleanup_stale_locks(max_age_seconds=5)
    assert cleaned == 0
