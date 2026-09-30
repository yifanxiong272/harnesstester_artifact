import os
import time
import shutil
import tempfile

import pytest

from openhands.runtime.utils.port_lock import cleanup_stale_locks

LOCK_DIR = os.path.join(tempfile.gettempdir(), 'openhands_port_locks')


def _ensure_clean_dir():
    # Remove the lock dir if it exists to create deterministic starting state
    if os.path.exists(LOCK_DIR):
        shutil.rmtree(LOCK_DIR)


def _make_dir():
    os.makedirs(LOCK_DIR, exist_ok=True)


def _touch(path, mtime=None):
    # Create a file and set its modification time deterministically
    with open(path, 'w') as f:
        f.write('lock')
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def test_cleanup_no_dir_round_057():
    """When the lock directory does not exist, cleanup_stale_locks returns 0."""
    _ensure_clean_dir()
    # Ensure directory truly does not exist
    assert not os.path.exists(LOCK_DIR)
    cleaned = cleanup_stale_locks(max_age_seconds=10)
    assert cleaned == 0


def test_cleanup_removes_stale_files_round_057():
    """Stale files matching pattern are removed; non-matching or recent files remain."""
    _ensure_clean_dir()
    _make_dir()
    try:
        now = time.time()
        # stale file: older than max_age_seconds
        stale = os.path.join(LOCK_DIR, 'port_123.lock')
        _touch(stale, mtime=now - 60)

        # recent file: should not be removed
        recent = os.path.join(LOCK_DIR, 'port_124.lock')
        _touch(recent, mtime=now)

        # non-matching file: should be ignored
        other = os.path.join(LOCK_DIR, 'notaport.lock')
        _touch(other, mtime=now - 60)

        # Use a small max_age_seconds so the stale file is removed deterministically
        cleaned = cleanup_stale_locks(max_age_seconds=5)

        assert cleaned == 1
        # stale should be removed
        assert 'port_123.lock' not in os.listdir(LOCK_DIR)
        # recent should remain
        assert 'port_124.lock' in os.listdir(LOCK_DIR)
        # non-matching should remain
        assert 'notaport.lock' in os.listdir(LOCK_DIR)
    finally:
        _ensure_clean_dir()


def test_cleanup_handles_os_errors_and_stat_failures_round_057(monkeypatch):
    """Ensure inner exceptions from os.stat or os.unlink and outer OSError during listdir are handled gracefully.

    Note: do not use os.path.exists while os.stat is monkeypatched because exists() calls stat internally.
    Instead, verify presence by listing directory contents.
    """
    _ensure_clean_dir()
    _make_dir()

    try:
        # Create a normal candidate file
        path = os.path.join(LOCK_DIR, 'port_broken.lock')
        _touch(path, mtime=time.time() - 60)

        # 1) Simulate os.stat raising FileNotFoundError for our specific path
        original_stat = os.stat

        def fake_stat(p):
            if os.path.normpath(p) == os.path.normpath(path):
                raise FileNotFoundError("simulated stat failure")
            return original_stat(p)

        monkeypatch.setattr(os, 'stat', fake_stat)
        cleaned = cleanup_stale_locks(max_age_seconds=5)
        # Because stat failed for that path, the code should skip removal and return 0
        assert cleaned == 0
        # Do not call os.path.exists (it uses os.stat). Instead, check directory listing.
        assert 'port_broken.lock' in os.listdir(LOCK_DIR)

        # 2) Simulate outer os.listdir raising OSError
        def fake_listdir(p):
            raise OSError("simulated listdir failure")

        monkeypatch.setattr(os, 'listdir', fake_listdir)
        cleaned2 = cleanup_stale_locks(max_age_seconds=5)
        assert cleaned2 == 0

    finally:
        _ensure_clean_dir()
