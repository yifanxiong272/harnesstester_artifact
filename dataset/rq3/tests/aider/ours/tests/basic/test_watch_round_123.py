import pytest
from types import SimpleNamespace

import aider.watch as watch_module

# All tests and helper names end with _round_123 per contract

def test_watch_files_handles_changes_and_returns_round_123(monkeypatch):
    """Ensure that when the watch generator yields changes and handle_changes returns True,
    watch_files exits early and the mocked watch received the expected kwargs.
    """
    seen = {}

    # Create a FileWatcher instance without calling __init__ to avoid external deps
    watcher = object.__new__(watch_module.FileWatcher)

    # Provide required attributes used by watch_files
    watcher.filter_func = lambda change_type, path: True
    watcher.stop_event = object()
    watcher.verbose = False

    # Simulate get_roots_to_watch returning a sequence of roots
    watcher.get_roots_to_watch = lambda: ("/tmp/root",)

    # handle_changes should be called with the yielded changes and then return True to stop
    def handle_changes(changes):
        seen['changes'] = changes
        return True

    watcher.handle_changes = handle_changes

    # Create a mock watch generator that asserts it received the exact objects and yields once
    def mock_watch(*roots, watch_filter=None, stop_event=None, ignore_permission_denied=False):
        # Assert called with the roots we provided
        assert roots == ("/tmp/root",)
        # Ensure the filter_func object passed is the same we set
        assert watch_filter is watcher.filter_func
        # Ensure stop_event identity is preserved
        assert stop_event is watcher.stop_event
        # yield a changes payload (structure opaque to FileWatcher, passed through)
        yield [(1, "/some/path")]

    monkeypatch.setattr(watch_module, "watch", mock_watch)

    # Call the method under test
    result = watch_module.FileWatcher.watch_files(watcher)

    # Because handle_changes returned True, watch_files should return early (None)
    assert result is None
    # And handle_changes should have been invoked with the yielded changes
    assert seen['changes'] == [(1, "/some/path")]


def test_watch_files_continues_then_exhausts_round_123(monkeypatch):
    """When handle_changes returns False for some yields, watch_files should continue until
    the watch generator is exhausted and then exit normally.
    """
    calls = []
    watcher = object.__new__(watch_module.FileWatcher)
    watcher.filter_func = lambda change_type, path: False
    watcher.stop_event = object()
    watcher.verbose = False
    watcher.get_roots_to_watch = lambda: ("/a", "/b")

    # handle_changes will append each call and always return False
    def handle_changes(changes):
        calls.append(tuple(changes))
        return False

    watcher.handle_changes = handle_changes

    # Mock watch yields three different change lists then stops
    def mock_watch(*roots, watch_filter=None, stop_event=None, ignore_permission_denied=False):
        # verify multiple roots passed through
        assert roots == ("/a", "/b")
        assert watch_filter is watcher.filter_func
        assert stop_event is watcher.stop_event
        yield [("c1",)]
        yield [("c2",)]
        yield [("c3",)]
        return

    monkeypatch.setattr(watch_module, "watch", mock_watch)

    # Should complete without raising
    result = watch_module.FileWatcher.watch_files(watcher)
    assert result is None
    # Ensure handle_changes called for each yielded changes list
    assert calls == [("c1",), ("c2",), ("c3",)]


def test_watch_files_get_roots_exception_triggers_dump_and_reraise_round_123(monkeypatch):
    """If get_roots_to_watch raises, and verbose is True, dump should be called with the
    formatted error and the original exception should be re-raised.
    """
    watcher = object.__new__(watch_module.FileWatcher)
    watcher.filter_func = lambda *a, **k: None
    watcher.stop_event = object()
    watcher.verbose = True

    # Make get_roots_to_watch raise an exception
    class MyErr(Exception):
        pass

    def raising_get_roots():
        raise MyErr("boom")

    watcher.get_roots_to_watch = raising_get_roots

    # Capture dump calls
    captured = {}

    def fake_dump(msg):
        captured['msg'] = msg

    monkeypatch.setattr(watch_module, 'dump', fake_dump)

    # Ensure that the underlying exception propagates
    with pytest.raises(MyErr):
        watch_module.FileWatcher.watch_files(watcher)

    # Verify dump was called with the expected formatting including the original message
    assert 'File watcher error: boom' in captured.get('msg', '')
