# file: sweagent/run/inspector_cli.py:417-425
# asked: {"lines": [417, 418, 419, 420, 421, 422, 423, 424], "branches": []}
# gained: {"lines": [417, 418, 419, 420, 421, 422, 423, 424], "branches": []}

import pathlib
from types import SimpleNamespace
import builtins
import inspect

import pytest

from sweagent.run.inspector_cli import TrajectoryInspectorApp


class FakeViewer:
    def __init__(self):
        self.called = False
        self.args = None
        self.kwargs = None

    def load_trajectory(self, path_arg, title_arg, stats_arg, *, gold_patch=None):
        # record call and arguments for assertions
        self.called = True
        self.args = (path_arg, title_arg, stats_arg)
        self.kwargs = {"gold_patch": gold_patch}


def make_app_with_state(path: pathlib.Path, trajectory_index=0, overview_stats=None, gold_patch_value="gold"):
    """
    Create a TrajectoryInspectorApp instance without invoking its __init__,
    and attach the minimal attributes/methods needed for _load_traj to run.
    """
    app = TrajectoryInspectorApp.__new__(TrajectoryInspectorApp)

    # required attributes used by _load_traj
    app.available_traj_paths = [path]
    app.trajectory_index = trajectory_index
    if overview_stats is None:
        # default mapping from stem to some stats object
        overview_stats = {path.stem: {"some": "stats"}}
    app.overview_stats = overview_stats

    # replace methods used by _load_traj
    app._get_viewer_title = lambda idx: f"title-for-{idx}"
    app.get_gold_patch = lambda instance_id: gold_patch_value

    # query_one will be patched by tests to return a FakeViewer instance
    return app


def test_load_traj_calls_viewer_with_expected_args():
    # Arrange
    p = pathlib.Path("/tmp/some_instance.traj")
    fake_viewer = FakeViewer()
    app = make_app_with_state(p, overview_stats={p.stem: {"k": "v"}}, gold_patch_value="gold-patch-value")

    # monkeypatch the query_one method to return our fake viewer and assert the incoming query type
    def fake_query_one(query_cls):
        # ensure the code passes a class-like identifier (TrajectoryViewer) but we don't require exact equality
        assert inspect.isclass(query_cls) or isinstance(query_cls, type) or hasattr(query_cls, "__name__")
        return fake_viewer

    app.query_one = fake_query_one

    # Act
    app._load_traj()

    # Assert
    assert fake_viewer.called is True, "Viewer.load_trajectory was not called"
    expected_path = p
    expected_title = "title-for-0"
    expected_stats = {"k": "v"}
    assert fake_viewer.args == (expected_path, expected_title, expected_stats)
    assert fake_viewer.kwargs == {"gold_patch": "gold-patch-value"}


def test_load_traj_passes_none_gold_patch_and_handles_complex_stem():
    # Arrange: filename with multiple dots to ensure .stem behavior is used
    p = pathlib.Path("/data/complex.name.with.dots.traj")
    instance_id = p.stem  # "complex.name.with.dots"
    stats_obj = {"n": 42}
    fake_viewer = FakeViewer()
    app = make_app_with_state(p, overview_stats={instance_id: stats_obj}, gold_patch_value=None)

    # Replace query_one to return the fake viewer
    app.query_one = lambda q: fake_viewer

    # Also override _get_viewer_title to return a known title for a non-zero index (change index to 0 still)
    app._get_viewer_title = lambda idx: "complex-title"

    # Act
    app._load_traj()

    # Assert that load_trajectory was called with the exact objects we provided and gold_patch=None
    assert fake_viewer.called is True
    assert fake_viewer.args[0] is p
    assert fake_viewer.args[1] == "complex-title"
    assert fake_viewer.args[2] is stats_obj
    assert fake_viewer.kwargs == {"gold_patch": None}
