# file: rdagent/log/ui/app.py:370-421
# asked: {"lines": [370, 371, 373, 374, 375, 376, 377, 379, 380, 381, 382, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 400, 401, 403, 405, 406, 407, 408, 409, 410, 411, 412, 414, 416, 418, 419, 420, 421], "branches": [[384, 385], [384, 386], [386, 387], [386, 403], [405, 406], [405, 414], [406, 407], [406, 414], [407, 406], [407, 408]]}
# gained: {"lines": [370, 371, 373, 374, 375, 376, 377, 379, 380, 381, 382, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 400, 401, 403, 405, 406, 407, 408, 409, 410, 411, 412, 414, 416, 418, 419, 420, 421], "branches": [[384, 385], [384, 386], [386, 387], [386, 403], [405, 406], [405, 414], [406, 407], [406, 414], [407, 406], [407, 408]]}

import importlib
import sys
from types import SimpleNamespace

import pandas as pd
import streamlit as st
import pytest


class SimpleHypothesis:
    def __init__(self, hypothesis):
        self.hypothesis = hypothesis


def _clear_state_keys(*keys):
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def _import_ui_app_with_patched_args(monkeypatch):
    # Patch ArgumentParser.parse_args to avoid module-level argparse.parse_args side-effects
    import argparse

    def fake_parse_args(self):
        return SimpleNamespace(log_dir=None, debug=False)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", fake_parse_args)

    # Ensure module is reloaded under the patched parse_args
    mod_name = "rdagent.log.ui.app"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    module = importlib.import_module(mod_name)
    return module


def test_metrics_window_without_alpha_baseline(monkeypatch):
    ui_app = _import_ui_app_with_patched_args(monkeypatch)

    # Prepare session state: no alpha_baseline_metrics
    st.session_state.hypotheses = [SimpleHypothesis("test hypothesis 0"), SimpleHypothesis("test hypothesis 1")]
    st.session_state.h_decisions = [True, False]
    st.session_state.alpha_baseline_metrics = None

    df = pd.DataFrame(
        {"colA": [1.1, 2.2], "colB": [3.3, 4.4]},
        index=["Alpha 0", "Alpha 1"],
    )

    captured = {}

    def fake_plotly_chart(fig, *args, **kwargs):
        captured["fig"] = fig

    def fake_download_button(label, data, file_name, mime, *args, **kwargs):
        captured["download"] = {
            "label": label,
            "data_obj": data,
            "file_name": file_name,
            "mime": mime,
            "bytes": data.getvalue() if hasattr(data, "getvalue") else None,
        }
        return "downloaded"

    monkeypatch.setattr(st, "plotly_chart", fake_plotly_chart)
    monkeypatch.setattr(st, "download_button", fake_download_button)

    try:
        ui_app.metrics_window(df, R=1, C=2, height=123, colors=["red", "green"])

        assert "fig" in captured, "plotly_chart was not called"
        fig = captured["fig"]
        assert len(fig.data) == 2
        assert fig.layout.height == 123
        # Marker colors set to provided colors
        assert getattr(fig.data[0], "marker")["color"] == "red"
        assert getattr(fig.data[1], "marker")["color"] == "green"
        # Hovertext content assertions
        hover0 = fig.data[0].hovertext[0]
        assert "test hypothesis 0" in hover0
        assert "color: green" in hover0
        hover1 = fig.data[0].hovertext[1]
        assert "test hypothesis 1" in hover1
        assert "color: black" in hover1

        # Download assertions
        assert "download" in captured
        dl = captured["download"]
        assert dl["label"] == "download the metrics (csv)"
        assert dl["file_name"] == "metrics.csv"
        assert dl["mime"] == "text/csv"
        expected_csv_bytes = df.to_csv().encode()
        assert dl["bytes"] == expected_csv_bytes
    finally:
        _clear_state_keys("hypotheses", "h_decisions", "alpha_baseline_metrics")


def test_metrics_window_with_alpha_baseline(monkeypatch):
    ui_app = _import_ui_app_with_patched_args(monkeypatch)

    st.session_state.hypotheses = [SimpleHypothesis("hb0"), SimpleHypothesis("hb1")]
    st.session_state.h_decisions = [False, True]
    st.session_state.alpha_baseline_metrics = {"some": "value"}

    df = pd.DataFrame(
        {"metric1": [0.1, 0.2, 0.3], "metric2": [1.1, 1.2, 1.3]},
        index=["Alpha Base", "Alpha 0", "Alpha 1"],
    )

    captured = {}

    def fake_plotly_chart(fig, *args, **kwargs):
        captured["fig"] = fig

    def fake_download_button(label, data, file_name, mime, *args, **kwargs):
        captured["download"] = {
            "label": label,
            "data_obj": data,
            "file_name": file_name,
            "mime": mime,
            "bytes": data.getvalue() if hasattr(data, "getvalue") else None,
        }
        return "downloaded"

    monkeypatch.setattr(st, "plotly_chart", fake_plotly_chart)
    monkeypatch.setattr(st, "download_button", fake_download_button)

    try:
        ui_app.metrics_window(df, R=1, C=2, height=200, colors=None)

        assert "fig" in captured
        fig = captured["fig"]
        assert len(fig.data) == 2
        assert fig.layout.height == 200

        # Check that ticktext was styled for Alpha Base on both x axes
        ticktext_axis1 = fig.layout.xaxis.ticktext
        ticktext_axis2 = fig.layout.xaxis2.ticktext
        styled_first = f'<span style="color:blue; font-weight:bold">{df.index[0]}</span>'
        assert ticktext_axis1[0] == styled_first
        assert ticktext_axis2[0] == styled_first

        # First hovertext element should be "Baseline"
        assert fig.data[0].hovertext[0] == "Baseline"

        # Download assertions
        assert "download" in captured
        dl = captured["download"]
        assert dl["label"] == "download the metrics (csv)"
        assert dl["file_name"] == "metrics.csv"
        assert dl["mime"] == "text/csv"
        expected_csv_bytes = df.to_csv().encode()
        assert dl["bytes"] == expected_csv_bytes
    finally:
        _clear_state_keys("hypotheses", "h_decisions", "alpha_baseline_metrics")
