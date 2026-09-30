import builtins
from pathlib import Path
import pytest

import sweagent.run.run_single as rs


def _make_problem_statement(pid: str):
    class P:
        def __init__(self, id_):
            self.id = id_
    return P(pid)


def test_init_calls_add_hook_for_each_hook_round_127(monkeypatch, tmp_path):
    # Arrange: recorders for patched call sites
    added_hooks = []
    file_handler_calls = []

    def fake_add_file_handler(path, level, id_=None):
        # record the string form to make assertions deterministic
        file_handler_calls.append((str(path), level, id_))

    def fake_get_logger(*args, **kwargs):
        # return a harmless logger-like object
        return object()

    class DummyCombinedRunHooks:
        def __init__(self):
            # simple placeholder, no external side effects
            self._v = True

    # Monkeypatch module-level collaborators before constructing RunSingle
    monkeypatch.setattr(rs, "add_file_handler", fake_add_file_handler)
    monkeypatch.setattr(rs, "get_logger", fake_get_logger)
    monkeypatch.setattr(rs, "CombinedRunHooks", DummyCombinedRunHooks)

    # Patch the add_hook method on the class so __init__ calls our recorder
    def _recorder_add_hook(self, hook):
        added_hooks.append(hook)

    monkeypatch.setattr(rs.RunSingle, "add_hook", _recorder_add_hook, raising=True)

    # Prepare constructor arguments
    env = object()
    agent = object()
    instance_id = "inst-123"
    problem_statement = _make_problem_statement(instance_id)
    hooks = [object(), object()]

    # Act
    inst = rs.RunSingle(
        env=env,
        agent=agent,
        problem_statement=problem_statement,
        output_dir=tmp_path,
        hooks=hooks,
        actions=None,
    )

    # Assert: add_hook was called exactly for each provided hook in order
    assert added_hooks == hooks

    # Assert: the logger/file handler setup executed deterministically for 3 levels
    assert len(file_handler_calls) == 3
    levels = [call[1] for call in file_handler_calls]
    assert set(levels) == {"trace", "debug", "info"}

    # Each path should include the instance id and the corresponding level filename
    paths = [call[0] for call in file_handler_calls]
    assert any(p.endswith(f"{instance_id}.trace.log") for p in paths)
    assert any(p.endswith(f"{instance_id}.debug.log") for p in paths)
    assert any(p.endswith(f"{instance_id}.info.log") for p in paths)

    # Ensure constructor preserved actions as passed (None) and attached the problem statement
    assert inst.actions is None
    assert inst.problem_statement is problem_statement


def test_init_does_not_call_add_hook_when_hooks_none_round_127(monkeypatch, tmp_path):
    # Arrange: patch add_hook to raise if called to ensure branch not taken
    def should_not_be_called(self, hook):
        raise AssertionError("add_hook should not be called when hooks is None")

    file_handler_calls = []

    def fake_add_file_handler(path, level, id_=None):
        file_handler_calls.append((str(path), level, id_))

    monkeypatch.setattr(rs, "add_file_handler", fake_add_file_handler)
    monkeypatch.setattr(rs, "get_logger", lambda *a, **k: object())
    monkeypatch.setattr(rs, "CombinedRunHooks", lambda: object())

    monkeypatch.setattr(rs.RunSingle, "add_hook", should_not_be_called, raising=True)

    env = object()
    agent = object()
    problem_statement = _make_problem_statement("no-hooks")

    # Act: should not raise
    inst = rs.RunSingle(
        env=env,
        agent=agent,
        problem_statement=problem_statement,
        output_dir=tmp_path,
        hooks=None,
        actions=None,
    )

    # Assert: no add_hook calls happened (would have raised)
    # Also verify file handlers still set up
    assert len(file_handler_calls) == 3
    assert inst.problem_statement is problem_statement
