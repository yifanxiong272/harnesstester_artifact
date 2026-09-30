# file: sweagent/run/inspector_cli.py:178-191
# asked: {"lines": [178, 180, 181, 182, 183, 184, 185, 186, 188, 189, 191], "branches": [[182, 183], [182, 191], [186, 188], [186, 189]]}
# gained: {"lines": [178, 180, 181, 182, 183, 184, 185, 186, 188, 189, 191], "branches": [[182, 183], [182, 191], [186, 188], [186, 189]]}

import os
from pathlib import Path

import pytest

from sweagent.run.inspector_cli import TrajectorySelectorScreen


def _make_overview(exit_status, result, cost, api_calls):
    return {"exit_status": exit_status, "result": result, "cost": float(cost), "api_calls": int(api_calls)}


def _new_screen_with_overview(overview_stats: dict):
    # Create instance without calling ModalScreen.__init__ to avoid UI dependencies
    screen = object.__new__(TrajectorySelectorScreen)
    screen.overview_stats = overview_stats
    return screen


def test_get_list_item_texts_no_duplicate_instance():
    # Two trajectories in different subfolders so that Path.stem != parent.name
    p1 = Path("/tmp/projects/a/123.traj")
    p2 = Path("/tmp/projects/b/456.traj")
    paths = [p1, p2]

    overview = {
        p1.stem: _make_overview("OK", "success", 1.5, 10),
        p2.stem: _make_overview("FAIL", "error", 2.0, 4),
    }

    screen = _new_screen_with_overview(overview)

    labels = screen._get_list_item_texts(paths)

    # Compute expected shortened paths: common prefix is /tmp/projects
    prefix = os.path.commonpath([str(p) for p in paths])
    expected_short1 = str(p1)[len(prefix) :].lstrip("/\\")
    expected_short2 = str(p2)[len(prefix) :].lstrip("/\\")
    expected1 = f"{expected_short1} - OK success $1.50 10 calls"
    expected2 = f"{expected_short2} - FAIL error $2.00 4 calls"

    assert labels == [expected1, expected2]


def test_get_list_item_texts_duplicate_instance_id_twice():
    # Create two paths so common prefix is '/tmp/projects' and the first path has duplicated instance id:
    # '/tmp/projects/c/c.traj' -> shortened 'c/c.traj' -> duplicated instance id -> becomes 'c'
    p_dup = Path("/tmp/projects/c/c.traj")
    p_other = Path("/tmp/projects/other/xyz.traj")
    paths = [p_dup, p_other]

    overview = {
        p_dup.stem: _make_overview("EXIT", "done", 0.0, 1),
        p_other.stem: _make_overview("RUN", "pending", 3.1415, 2),
    }

    screen = _new_screen_with_overview(overview)

    labels = screen._get_list_item_texts(paths)

    # For the duplicated path we expect only the stem 'c' (since parent folder is also 'c')
    # For the other path expect normal shortened form
    prefix = os.path.commonpath([str(p) for p in paths])
    shortened_dup = str(p_dup)[len(prefix) :].lstrip("/\\")
    # verify the code path: shortened_dup should be 'c/c.traj'
    assert shortened_dup.startswith("c/") and "c.traj" in shortened_dup

    # Apply the same transformation as the implementation to compute expected strings
    if Path(shortened_dup).stem == Path(shortened_dup).parent.name:
        shortened_dup_expected = Path(shortened_dup).stem
    else:
        shortened_dup_expected = shortened_dup

    shortened_other = str(p_other)[len(prefix) :].lstrip("/\\")
    expected_dup = f"{shortened_dup_expected} - EXIT done $0.00 1 calls"
    expected_other = f"{shortened_other} - RUN pending $3.14 2 calls"

    assert labels == [expected_dup, expected_other]
