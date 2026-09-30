# file: rdagent/log/ui/app.py:370-421
# asked: {"lines": [370, 371, 373, 374, 375, 376, 377, 379, 380, 381, 382, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 400, 401, 403, 405, 406, 407, 408, 409, 410, 411, 412, 414, 416, 418, 419, 420, 421], "branches": [[384, 385], [384, 386], [386, 387], [386, 403], [405, 406], [405, 414], [406, 407], [406, 414], [407, 406], [407, 408]]}
# gained: {"lines": [370, 371, 373, 374, 375, 376, 377, 379, 380, 381, 382, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 400, 401, 403, 405, 406, 407, 408, 409, 410, 411, 412, 414, 416, 418, 419, 420, 421], "branches": [[384, 385], [384, 386], [386, 387], [386, 403], [405, 406], [405, 414], [406, 407], [406, 414], [407, 406], [407, 408]]}

import importlib
import sys
from types import SimpleNamespace

import pandas as pd
import pytest


def import_app_fresh(monkeypatch):
    # Ensure argparse in module reads no pytest args by setting argv to only program name
    monkeypatch.setattr(sys, "argv", ["prog"])
    # Remove cached module so import runs module-level code under controlled argv
    sys.modules.pop("rdagent.log.ui.app", None)
    app = importlib.import_module("rdagent.log.ui.app")
    return app


def test_metrics_window_without_alpha_baseline(monkeypatch):
    app = import_app_fresh(monkeypatch)

    df = pd.DataFrame(
        {"colA": [1, 2], "colB": [3, 4]},
        index=["Metric0", "Metric1"],
    )

    hypo0 = SimpleNamespace(hypothesis="short hypothesis text")
    hypo1 = SimpleNamespace(hypothesis="another hypothesis")
    state_obj = SimpleNamespace(
        hypotheses={0: hypo0, 1: hypo1},
        h_decisions={0: True, 1: False},
        alpha_baseline_metrics=None,
    )
    monkeypatch.setattr(app, "state", state_obj)

    captured = {}

    def fake_plotly_chart(fig):
        captured["fig"] = fig

    def fake_download_button(label, data, file_name, mime):
        captured["label"] = label
        captured["data"] = data
        captured["file_name"] = file_name
        captured["mime"] = mime
        return "downloaded"

    monkeypatch.setattr(app, "st", SimpleNamespace(plotly_chart=fake_plotly_chart, download_button=fake_download_button))

    app.metrics_window(df, 1, 2, height=400, colors=None)

    assert "fig" in captured
    fig = captured["fig"]
    assert hasattr(fig, "layout")
    assert fig.layout.height == 400

    assert captured["label"] == "download the metrics (csv)"
    assert captured["file_name"] == "metrics.csv"
    assert captured["mime"] == "text/csv"
    buffer = captured["data"]
    buffer.seek(0)
    content = buffer.getvalue().decode()
    assert content == df.to_csv()


def test_metrics_window_with_alpha_baseline_and_colors(monkeypatch):
    app = import_app_fresh(monkeypatch)

    df = pd.DataFrame({"only": [10, 20]}, index=["Baseline", "Metric0"])

    hypo0 = SimpleNamespace(hypothesis="a long hypothesis that will be wrapped " * 3)
    state_obj = SimpleNamespace(
        hypotheses={0: hypo0},
        h_decisions={0: False},
        alpha_baseline_metrics={"some": "value"},
    )
    monkeypatch.setattr(app, "state", state_obj)

    captured = {}

    def fake_plotly_chart(fig):
        captured["fig"] = fig

    def fake_download_button(label, data, file_name, mime):
        captured["data"] = data
        captured["label"] = label
        captured["file_name"] = file_name
        captured["mime"] = mime
        return None

    monkeypatch.setattr(app, "st", SimpleNamespace(plotly_chart=fake_plotly_chart, download_button=fake_download_button))

    app.metrics_window(df, 1, 1, colors=["red"])

    assert "fig" in captured
    fig = captured["fig"]

    # Access xaxis ticktext; depending on plotly version it might be a tuple/list-like
    xaxis = getattr(fig.layout, "xaxis", None)
    assert xaxis is not None
    ticktext = list(xaxis.ticktext) if xaxis.ticktext is not None else []
    assert ticktext, "ticktext should have been set when alpha_baseline_metrics is not None"
    assert df.index[0] in ticktext[0]
    assert 'color:blue' in ticktext[0] and 'font-weight:bold' in ticktext[0]

    assert len(fig.data) >= 1
    trace = fig.data[0]
    assert hasattr(trace, "marker")
    assert getattr(trace.marker, "color") == "red"

    buffer = captured["data"]
    buffer.seek(0)
    assert buffer.getvalue().decode() == df.to_csv()
