# file: aider/watch.py:172-179
# asked: {"lines": [174, 175, 176, 177, 178, 179], "branches": [[174, 175], [174, 176], [176, 0], [176, 177]]}
# gained: {"lines": [174, 175, 176, 177, 178, 179], "branches": [[174, 175], [176, 0], [176, 177]]}

import types
from unittest.mock import Mock
from pathlib import Path

import pytest

from aider.watch import FileWatcher


class DummyIO:
    pass


def make_coder(tmp_path):
    coder = types.SimpleNamespace()
    coder.io = DummyIO()
    coder.root = tmp_path
    return coder


def test_stop_with_both_event_and_thread(tmp_path):
    coder = make_coder(tmp_path)
    fw = FileWatcher(coder, gitignores=None, verbose=False, analytics=None, root=None)

    # verify constructor set the file_watcher on io
    assert getattr(coder.io, "file_watcher") is fw

    # attach mocks to simulate a running watcher
    mock_event = Mock()
    mock_thread = Mock()
    fw.stop_event = mock_event
    fw.watcher_thread = mock_thread

    # call stop and verify behavior
    fw.stop()

    mock_event.set.assert_called_once()
    mock_thread.join.assert_called_once()

    # ensure attributes were cleared
    assert fw.watcher_thread is None
    assert fw.stop_event is None


def test_stop_with_only_stop_event(tmp_path):
    coder = make_coder(tmp_path)
    fw = FileWatcher(coder, gitignores=None, verbose=False, analytics=None, root=None)

    mock_event = Mock()
    fw.stop_event = mock_event
    fw.watcher_thread = None

    # call stop and verify only the event was set and not cleared (since no thread)
    fw.stop()

    mock_event.set.assert_called_once()
    assert fw.watcher_thread is None
    # According to implementation, stop_event is only cleared if watcher_thread existed,
    # so it should still be the mock_event here.
    assert fw.stop_event is mock_event
