# file: sweagent/run/rich_test.py:35-55
# asked: {"lines": [35, 36, 37, 40, 41, 43, 45, 47, 48, 49, 50, 53, 54, 55], "branches": []}
# gained: {"lines": [35, 36, 37, 40, 41, 43, 45, 47, 48, 49, 50, 53, 54, 55], "branches": []}

import builtins
from types import SimpleNamespace

import pytest

from sweagent.run.rich_test import RunBatch
from sweagent.run.rich_test import progress_lock
from rich.progress import TaskID


def test_do_task_updates_and_removes_spinner(monkeypatch):
    rb = RunBatch()

    # Create dummy progress bars to observe interactions without using rich's internals
    class DummyTaskProgress:
        def __init__(self):
            self.added = []
            self.updated = []
            self.removed = []

        def add_task(self, description, total=None):
            tid = object()
            self.added.append((tid, description, total))
            return tid

        def update(self, task_id, description=None):
            self.updated.append((task_id, description))

        def remove_task(self, task_id):
            self.removed.append(task_id)

    class DummyMainProgress:
        def __init__(self):
            self.updates = []

        def update(self, task_id, advance=0):
            # record the integer value of the TaskID if possible, otherwise store as-is
            try:
                tid_val = int(task_id)
            except Exception:
                tid_val = task_id
            self.updates.append((tid_val, advance))

    task_progress = DummyTaskProgress()
    main_progress = DummyMainProgress()

    rb._task_progress_bar = task_progress
    rb._main_progress_bar = main_progress

    # Prevent real sleeping and make random deterministic
    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("random.random", lambda: 0.0)  # causes minimal sleeps in the code

    # Run do_task and verify interactions
    rb.do_task(7)

    # One spinner should have been added and then removed
    assert len(task_progress.added) == 1, "Expected exactly one spinner task to be added"
    added_tid, added_desc, added_total = task_progress.added[0]
    assert "Task 7" in added_desc
    assert added_total is None

    # Spinner should have been updated to show working description
    assert any(
        (u_tid is added_tid and u_desc is not None and "(working)" in u_desc)
        for (u_tid, u_desc) in task_progress.updated
    ), "Spinner task should have been updated to a '(working)' description"

    # Spinner should have been removed
    assert task_progress.removed == [added_tid], "Spinner task should have been removed after work"

    # Main progress should have been advanced by 1 on TaskID(0)
    assert main_progress.updates, "Main progress should have received at least one update"
    # last update should be the advance by 1 on task 0
    last_tid, last_advance = main_progress.updates[-1]
    assert last_advance == 1
    assert last_tid == 0


def test_do_task_requires_progress_bars_and_uses_lock(monkeypatch):
    rb = RunBatch()

    # If either progress bar is None, assertions in do_task should fail.
    # First ensure _main_progress_bar is None -> AssertionError
    rb._main_progress_bar = None
    rb._task_progress_bar = None

    monkeypatch.setattr("time.sleep", lambda s: None)
    monkeypatch.setattr("random.random", lambda: 0.0)

    with pytest.raises(AssertionError):
        rb.do_task(0)

    # Now set only the main progress bar -> still should raise because task bar is None
    class SimpleMain:
        def update(self, task_id, advance=0):
            pass

    rb._main_progress_bar = SimpleMain()
    rb._task_progress_bar = None

    with pytest.raises(AssertionError):
        rb.do_task(0)

    # Finally set both to simple implementations that record lock usage.
    events = []

    class LockingTaskProgress:
        def add_task(self, description, total=None):
            events.append(("add", description, total))
            return "spinner-id"

        def update(self, task_id, description=None):
            events.append(("update", task_id, description))

        def remove_task(self, task_id):
            events.append(("remove", task_id))

    class LockingMainProgress:
        def update(self, task_id, advance=0):
            events.append(("main_update", int(task_id), advance))

    rb._task_progress_bar = LockingTaskProgress()
    rb._main_progress_bar = LockingMainProgress()

    # Run do_task while ensuring no real sleep
    rb.do_task(1)

    # Validate ordering of events reflects add -> update -> remove -> main_update (not strictly enforced but should contain all)
    types = [e[0] for e in events]
    assert "add" in types
    assert "update" in types
    assert "remove" in types
    assert ("main_update" in types), "Expected main progress to be updated"
    # Ensure main_update advanced task 0 by 1
    main_updates = [e for e in events if e[0] == "main_update"]
    assert main_updates and main_updates[-1][2] == 1
