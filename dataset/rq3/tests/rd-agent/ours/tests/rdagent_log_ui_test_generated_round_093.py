import sys
# Ensure argparse in the application won't see pytest's CLI args during import
_saved_argv = sys.argv.copy()
sys.argv = [sys.argv[0]]

import io
import pandas as pd
import types
import pytest

import rdagent.log.ui.app as app

# restore original argv to avoid side effects on the test runner
sys.argv = _saved_argv


class DummyHyp:
    def __init__(self, text):
        self.hypothesis = text


class FakeFig:
    def __init__(self):
        self.added_traces = []
        self.updated_layout = []
        self.updated_xaxes_calls = []

    def add_trace(self, trace, row=None, col=None):
        # store the trace and subplot position for assertions
        self.added_traces.append({"trace": trace, "row": row, "col": col})

    def update_layout(self, **kwargs):
        self.updated_layout.append(kwargs)

    def update_xaxes(self, **kwargs):
        self.updated_xaxes_calls.append(kwargs)


@pytest.fixture
def fake_plotting(monkeypatch):
    """Patch plotting and streamlit callbacks in the app module to deterministic fakes.
    Returns recorders for assertions.
    """
    fake_fig = FakeFig()

    # Patch make_subplots to return our fake figure
    def fake_make_subplots(rows, cols, subplot_titles=None):
        return fake_fig

    monkeypatch.setattr(app, "make_subplots", fake_make_subplots)

    # Patch go.Scatter to capture the kwargs passed and return them as a dict
    def fake_scatter(**kwargs):
        return dict(kwargs)

    monkeypatch.setattr(app.go, "Scatter", fake_scatter)

    # Capture plotly_chart call
    plotly_chart_calls = []

    def fake_plotly_chart(fig):
        plotly_chart_calls.append(fig)

    monkeypatch.setattr(app.st, "plotly_chart", fake_plotly_chart)

    # Capture download_button call
    download_calls = []

    def fake_download_button(label, data, file_name, mime):
        download_calls.append({"label": label, "data": data, "file_name": file_name, "mime": mime})

    monkeypatch.setattr(app.st, "download_button", fake_download_button)

    return {
        "fake_fig": fake_fig,
        "plotly_chart_calls": plotly_chart_calls,
        "download_calls": download_calls,
    }


def test_metrics_window_without_alpha_baseline_round_093(fake_plotting, monkeypatch):
    """Exercise branch where state.alpha_baseline_metrics is None and colors provided.

    Assertions:
    - One trace is added with hovertext built from state.hypotheses and state.h_decisions
    - plotly_chart and download_button are invoked
    - The downloaded buffer contains CSV text for the DataFrame
    """
    # Prepare a small dataframe with indexes matching the slicing logic i[6:]
    df = pd.DataFrame({"colA": [10, 20, 30]}, index=["Prefix0", "Prefix1", "Alpha Base"])

    # Prepare dummy state: hypotheses and decisions
    dummy_state = types.SimpleNamespace()
    # hypotheses must be indexable by integer obtained from i[6:]
    dummy_state.hypotheses = [DummyHyp("short hypothesis 0"), DummyHyp("short hypothesis 1")]
    # decisions: first False -> black, second True -> green
    dummy_state.h_decisions = [False, True]
    dummy_state.alpha_baseline_metrics = None

    monkeypatch.setattr(app, "state", dummy_state)

    # Call the function under test
    app.metrics_window(df, 1, 1, height=150, colors=["red"])

    # Inspect the fake figure
    fake_fig = fake_plotting["fake_fig"]

    # One trace added (one column)
    assert len(fake_fig.added_traces) == 1

    trace_dict = fake_fig.added_traces[0]["trace"]
    # The fake go.Scatter returns a dict of kwargs; hovertext key should be present
    assert "hovertext" in trace_dict

    hovertexts = trace_dict["hovertext"]
    # 'Alpha Base' should have been excluded, so two hovertexts expected
    assert isinstance(hovertexts, list) and len(hovertexts) == 2

    # Check that colors were applied via the hypothesis_hover_text logic
    # First decision False -> color black, second True -> color green
    assert "color: black" in hovertexts[0]
    assert "color: green" in hovertexts[1]

    # plotly_chart should have been called once with the fake figure
    assert len(fake_plotting["plotly_chart_calls"]) == 1

    # download_button should have been called once with file_name 'metrics.csv'
    assert len(fake_plotting["download_calls"]) == 1
    dl = fake_plotting["download_calls"][0]
    assert dl["file_name"] == "metrics.csv"
    assert dl["mime"] == "text/csv"

    # The data argument is a BytesIO-like object; ensure it contains the DataFrame CSV
    buf = dl["data"]
    buf.seek(0)
    # getvalue works for BytesIO; ensure column name and values present
    assert b"colA" in buf.getvalue()
    assert b"10" in buf.getvalue() and b"20" in buf.getvalue()


def test_metrics_window_with_alpha_baseline_updates_axes_round_093(fake_plotting, monkeypatch):
    """Exercise branch where state.alpha_baseline_metrics is present, triggering baseline insertion
    and update_xaxes calls across the R x C grid.

    Assertions:
    - Hovertexts start with 'Baseline'
    - update_xaxes is called for each subplot cell (R * C times)
    """
    # Two columns to exercise multiple add_trace calls
    df = pd.DataFrame({"colA": [1, 2], "colB": [3, 4]}, index=["Prefix0", "Prefix1"])

    # Prepare dummy state: hypotheses and decisions
    dummy_state = types.SimpleNamespace()
    dummy_state.hypotheses = [DummyHyp("h0"), DummyHyp("h1")]
    dummy_state.h_decisions = [True, False]
    # Non-None triggers baseline behavior
    dummy_state.alpha_baseline_metrics = {"some": "metrics"}

    monkeypatch.setattr(app, "state", dummy_state)

    R, C = 2, 2
    app.metrics_window(df, R, C, height=200, colors=None)

    fake_fig = fake_plotting["fake_fig"]

    # Hovertexts were passed into each added trace's scatter dict
    assert len(fake_fig.added_traces) == 2  # two columns -> two traces

    # For each trace, hovertext should start with 'Baseline' because alpha_baseline_metrics is not None
    for entry in fake_fig.added_traces:
        trace = entry["trace"]
        ht = trace.get("hovertext")
        assert isinstance(ht, list)
        assert ht[0] == "Baseline"

    # update_xaxes should have been called for each subplot cell: R * C times
    assert len(fake_fig.updated_xaxes_calls) == R * C

    # check one of the update_xaxes calls contains tickvals and ticktext as expected
    sample_call = fake_fig.updated_xaxes_calls[0]
    assert "tickvals" in sample_call and "ticktext" in sample_call
    # ticktext first element should contain a span with color:blue
    assert "color:blue" in sample_call["ticktext"][0]
