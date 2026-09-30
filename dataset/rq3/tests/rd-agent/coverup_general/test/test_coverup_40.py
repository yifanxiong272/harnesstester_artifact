# file: rdagent/log/ui/ds_summary.py:27-68
# asked: {"lines": [27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 62, 63, 64, 66, 67, 68], "branches": [[30, 31], [30, 67], [31, 32], [31, 67], [38, 39], [38, 45], [39, 40], [39, 44], [45, 46], [45, 48], [50, 51], [50, 53], [67, 0], [67, 68]]}
# gained: {"lines": [27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 62, 63, 64, 66, 67, 68], "branches": [[30, 31], [31, 32], [31, 67], [38, 39], [38, 45], [39, 40], [39, 44], [45, 46], [45, 48], [50, 51], [50, 53], [67, 0], [67, 68]]}

import types
import contextlib
import traceback as _traceback
import pandas as pd
import pytest

import rdagent.log.ui.ds_summary as ds_summary


class FakeColumn:
    def __init__(self, return_value):
        self._return = return_value

    def toggle(self, *args, **kwargs):
        return self._return


class FakeST:
    def __init__(self, cb1_toggle=False, cb2_toggle=False):
        self.cb1 = FakeColumn(cb1_toggle)
        self.cb2 = FakeColumn(cb2_toggle)

        # Recording calls
        self.markdowns = []
        self.warnings = []
        self.writes = []
        self.plotly_chart_calls = []
        self.codes = []
        self.jsons = []
        self.pyplts = []

    def columns(self, *args, **kwargs):
        return (self.cb1, self.cb2)

    @contextlib.contextmanager
    def container(self, *args, **kwargs):
        yield None

    def markdown(self, msg):
        self.markdowns.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def write(self, obj):
        self.writes.append(obj)

    def plotly_chart(self, fig):
        self.plotly_chart_calls.append(fig)

    def code(self, txt):
        self.codes.append(txt)

    def json(self, obj):
        self.jsons.append(obj)

    def pyplot(self, fig):
        self.pyplts.append(fig)


def make_vs_df(name='metric'):
    # Create a DataFrame with duplicated index and including 'ensemble'
    df = pd.DataFrame(
        {
            name: [0.1, 0.2, 0.3],
            'other': [1, 2, 3]
        },
        index=['a', 'ensemble', 'a']
    )
    # Name for the column (used later as Series.name)
    df.columns.name = None
    return df


def test_curves_win_success_with_ensemble_and_duplicates(monkeypatch):
    fake = FakeST(cb1_toggle=True, cb2_toggle=False)

    # Monkeypatch the st object in the module
    monkeypatch.setattr(ds_summary, "st", fake)

    recorded_vscores = []

    # Replace curve_figure to capture the argument and return a dummy figure
    def fake_curve_figure(vscores):
        # Record a copy so tests can inspect without being mutated later
        recorded_vscores.append(vscores.copy())
        return {"dummy": "figure"}

    monkeypatch.setattr(ds_summary, "curve_figure", fake_curve_figure)

    # Prepare summary with one entry that will exercise duplicate index and 'ensemble' row
    vs = make_vs_df(name='my_metric')
    summary = {
        "ModelX": {
            "competition": "comp1",
            "test_scores": {"t1": 0.5, "t2": 0.6},
            "valid_scores": {"loop1": vs}
        }
    }

    # Call the function under test
    ds_summary.curves_win(summary)

    # Assertions: curve_figure was called once and got a DataFrame with expected properties
    assert len(recorded_vscores) == 1
    passed_df = recorded_vscores[0]
    # After processing, columns name should be the metric name 'my_metric'
    assert passed_df.columns.name == "my_metric"
    # There should be a 'test' column
    assert "test" in passed_df.columns
    # Index values should be prefixed with 'L'
    assert all(str(idx).startswith("L") for idx in passed_df.index)
    # Duplicate warning should have been issued
    assert any("not unique" in w for w in fake.warnings)
    # The original DataFrame should have been written once due to duplicate handling
    assert any(isinstance(w, pd.DataFrame) for w in fake.writes)
    # plotly_chart should have been called with our dummy figure
    assert fake.plotly_chart_calls == [{"dummy": "figure"}]


def test_curves_win_exception_and_lite(monkeypatch):
    # This test will force curve_figure to raise to exercise the except branch,
    # and will also enable the lite branch to call lite_curve_figure & pyplot.
    fake = FakeST(cb1_toggle=True, cb2_toggle=True)
    monkeypatch.setattr(ds_summary, "st", fake)

    # Make curve_figure raise an exception to trigger the except block
    def bad_curve_figure(vscores):
        raise ValueError("forced failure")

    monkeypatch.setattr(ds_summary, "curve_figure", bad_curve_figure)

    # Make lite_curve_figure return a dummy plt object
    def fake_lite(summary):
        return {"lite": "plt"}

    monkeypatch.setattr(ds_summary, "lite_curve_figure", fake_lite)

    # Prepare a minimal summary; valid_scores contains a dict to be JSON-dumped in the except
    vs = pd.DataFrame({"m": [0.1]}, index=["x"])
    summary = {
        "ModelY": {
            "competition": "comp2",
            "test_scores": {"only": 0.9},
            "valid_scores": {"loopA": vs}
        }
    }

    ds_summary.curves_win(summary)

    # After exception, we should have recorded an error markdown mentioning the exception
    assert any("Error" in m or "forced failure" in m for m in fake.markdowns)
    # Code should have captured a traceback string
    assert len(fake.codes) >= 1
    assert "ValueError" in fake.codes[0] or "forced failure" in fake.codes[0]
    # JSON call should have been made with the valid_scores dict from the summary
    assert any(isinstance(j, dict) and "loopA" in j for j in fake.jsons)
    # Lite branch should invoke pyplot with our dummy lite figure
    assert fake.pyplts == [{"lite": "plt"}]


def test_curves_win_metric_name_none(monkeypatch):
    # This tests the branch when there are no valid_scores -> metric_name == 'None'
    fake = FakeST(cb1_toggle=True, cb2_toggle=False)
    monkeypatch.setattr(ds_summary, "st", fake)

    captured = []

    def capture_curve(vscores):
        captured.append(vscores.copy())
        return "ok"

    monkeypatch.setattr(ds_summary, "curve_figure", capture_curve)

    # valid_scores is empty dict -> len(vscores)==0 branch
    summary = {
        "ModelZ": {
            "competition": "comp3",
            "test_scores": {"a": 1.0, "b": 2.0},
            "valid_scores": {}
        }
    }

    ds_summary.curves_win(summary)

    # Ensure curve_figure was called and columns.name was set to 'None'
    assert len(captured) == 1
    df = captured[0]
    assert df.columns.name == "None"
    # 'test' column should exist and contain the test scores
    assert "test" in df.columns
    assert set(df["test"].tolist()) == {1.0, 2.0}
