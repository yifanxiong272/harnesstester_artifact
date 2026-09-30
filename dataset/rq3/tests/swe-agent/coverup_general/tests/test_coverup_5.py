# file: sweagent/run/remove_unfinished.py:13-46
# asked: {"lines": [13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46], "branches": [[16, 17], [16, 39], [17, 18], [17, 19], [19, 20], [19, 21], [22, 23], [22, 25], [25, 26], [25, 28], [35, 16], [35, 36], [39, 40], [39, 44], [41, 0], [41, 42], [44, 0], [44, 45]]}
# gained: {"lines": [13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46], "branches": [[16, 17], [16, 39], [17, 18], [17, 19], [19, 20], [19, 21], [22, 23], [22, 25], [25, 26], [25, 28], [35, 16], [35, 36], [39, 40], [39, 44], [41, 0], [41, 42], [44, 0], [44, 45]]}

import logging
from pathlib import Path

import pytest

from sweagent.run.remove_unfinished import remove_unfinished


def _make_dir_with_files(base: Path, name: str, traj_names=()):
    d = base / name
    d.mkdir()
    for t in traj_names:
        (d / t).write_text("traj")
    return d


def _fake_load_file_factory():
    """
    Returns a fake load_file function that:
    - raises for files named 'raise.traj'
    - returns {'info': {}} for 'nosub.traj'
    - returns {'info': {'submission': 'ok'}} for others
    """

    def fake_load_file(path):
        if path.name == "raise.traj":
            raise RuntimeError("boom")
        if path.name == "nosub.traj":
            return {"info": {}}
        return {"info": {"submission": "ok"}}

    return fake_load_file


def test_remove_unfinished_dry_run_logs(caplog, tmp_path, monkeypatch):
    caplog.set_level(logging.INFO)

    # Arrange
    base = tmp_path
    # top-level file (not directory) should be skipped
    (base / "afile.txt").write_text("hello")

    # directory without '__' in name should be skipped
    _make_dir_with_files(base, "nodbl", traj_names=("shouldnot.traj",))

    # directory with '__' but no traj files -> "No trajectories found"
    no_traj_dir = _make_dir_with_files(base, "a__1", traj_names=())

    # directory with '__' and multiple traj files -> warning "Found multiple trajectories..."
    multi_traj_dir = _make_dir_with_files(base, "b__2", traj_names=("one.traj", "two.traj"))

    # directory where load_file raises -> should be added to remove list
    raise_dir = _make_dir_with_files(base, "c__3", traj_names=("raise.traj",))

    # directory where load_file returns no submission -> should be added to remove list
    nosub_dir = _make_dir_with_files(base, "d__4", traj_names=("nosub.traj",))

    # Good directory (should be ignored/not removed)
    good_dir = _make_dir_with_files(base, "e__5", traj_names=("good.traj",))

    # Patch load_file in the module under test
    monkeypatch.setattr(
        "sweagent.run.remove_unfinished.load_file",
        _fake_load_file_factory(),
    )

    # Act
    remove_unfinished(base, dry_run=True)

    # Assert - check expected log messages
    logs = caplog.records
    messages = [r.getMessage() for r in logs]

    # "No trajectories found" for a__1
    assert any("No trajectories found in" in m and "a__1" in m for m in messages)

    # "Found multiple trajectories" for b__2
    assert any("Found multiple trajectories" in m and "b__2" in m for m in messages)

    # "Error loading trajectory" for c__3
    assert any("Error loading trajectory" in m and "raise.traj" in m for m in messages)

    # "No submission found" for d__4
    assert any("No submission found in" in m and "d__4" in m for m in messages)

    # Dry-run summary mentions 2 unfinished trajectories (c__3 and d__4)
    assert any("Would remove 2 unfinished trajectories." in m for m in messages)

    # The two directories slated for removal should be printed in the log (their path strings)
    assert any(str(raise_dir) in m for m in messages)
    assert any(str(nosub_dir) in m for m in messages)

    # Ensure good directory not slated for removal
    assert not any("e__5" in m and "Would remove" in m for m in messages)


def test_remove_unfinished_actual_removal(tmp_path, monkeypatch):
    # Arrange
    base = tmp_path

    # directory where load_file raises -> should be removed
    raise_dir = _make_dir_with_files(base, "x__r", traj_names=("raise.traj",))

    # directory where load_file returns no submission -> should be removed
    nosub_dir = _make_dir_with_files(base, "y__n", traj_names=("nosub.traj",))

    # directory with a proper submission -> should not be removed
    good_dir = _make_dir_with_files(base, "z__g", traj_names=("good.traj",))

    # Patch load_file
    monkeypatch.setattr(
        "sweagent.run.remove_unfinished.load_file",
        _fake_load_file_factory(),
    )

    # Record calls to rmtree
    removed = []

    def fake_rmtree(path):
        # record and actually remove so tmp_path stays clean
        removed.append(Path(path))
        # perform actual removal to mimic real behavior
        # Path(path) may be a Path already
        p = Path(path)
        if p.exists():
            # remove contents then dir
            for child in p.rglob("*"):
                if child.is_file():
                    child.unlink()
            p.rmdir()

    monkeypatch.setattr("sweagent.run.remove_unfinished.shutil.rmtree", fake_rmtree)

    # Act
    remove_unfinished(base, dry_run=False)

    # Assert
    # Both problematic directories should have been passed to rmtree
    removed_paths = [str(p) for p in removed]
    assert any(str(raise_dir) == p for p in removed_paths)
    assert any(str(nosub_dir) == p for p in removed_paths)

    # Good directory should not have been removed
    assert (base / "z__g").exists()
