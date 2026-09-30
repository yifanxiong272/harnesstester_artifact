# file: rdagent/log/ui/qlib_report_figure.py:348-445
# asked: {"lines": [348, 356, 359, 360, 362, 363, 364, 365, 366, 367, 368, 369, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 387, 388, 390, 391, 392, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 429, 430, 431, 432, 433, 434, 435, 437, 438, 439, 440, 441, 442, 443, 445], "branches": [[388, 390], [388, 394]]}
# gained: {"lines": [348, 356, 359, 360, 362, 363, 364, 365, 366, 367, 368, 369, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 387, 388, 390, 391, 392, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 429, 430, 431, 432, 433, 434, 435, 437, 438, 439, 440, 441, 442, 443, 445], "branches": [[388, 390], [388, 394]]}

import importlib
import pandas as pd
import pytest


MODULE_PATH = "rdagent.log.ui.qlib_report_figure"


@pytest.fixture
def module():
    return importlib.import_module(MODULE_PATH)


def make_sample_report_df():
    # Create a small DataFrame with the expected columns and an index name 'date'
    idx = pd.Index(["2020-01-01", "2020-01-02", "2020-01-03"], name="date")
    data = {
        "cum_bench": [1.0, 1.1, 1.2],
        "cum_return_wo_cost": [1.0, 1.05, 1.07],
        "cum_return_w_cost": [1.0, 1.04, 1.06],
        "return_wo_mdd": [0.0, -0.02, -0.01],
        "return_w_cost_mdd": [0.0, -0.03, -0.02],
        "cum_ex_return_wo_cost": [0.0, 0.02, 0.03],
        "cum_ex_return_w_cost": [0.0, 0.015, 0.025],
        "turnover": [0.1, 0.2, 0.15],
        "cum_ex_return_w_cost_mdd": [0.0, -0.01, 0.0],
        "cum_ex_return_wo_cost_mdd": [0.0, -0.005, 0.0],
    }
    return pd.DataFrame(data, index=idx)


def test_report_figure_produces_figure_and_layout_shapes(monkeypatch, module):
    # Prepare the fake report DataFrame that _calculate_report_data will return
    fake_report_df = make_sample_report_df()

    # Monkeypatch _calculate_report_data to return our fake DataFrame
    monkeypatch.setattr(module, "_calculate_report_data", lambda df: fake_report_df)

    # Monkeypatch _calculate_maximum to return different ranges for exclusive=False and True
    def fake_calc_maximum(df, exclusive=False):
        if exclusive:
            return ("2020-01-02", "2020-01-03")
        return ("2020-01-01", "2020-01-02")

    monkeypatch.setattr(module, "_calculate_maximum", fake_calc_maximum)

    # Create a fake SubplotsGraph that records what was passed and exposes .figure
    recorded = {}

    class FakeSubplotsGraph:
        def __init__(self, df, layout, sub_graph_data, subplots_kwargs, kind_map, sub_graph_layout):
            recorded["df"] = df.copy()
            recorded["layout"] = layout.copy()
            recorded["sub_graph_data"] = sub_graph_data
            recorded["subplots_kwargs"] = subplots_kwargs.copy()
            recorded["kind_map"] = kind_map.copy()
            recorded["sub_graph_layout"] = sub_graph_layout.copy()
            # Return a simple sentinel as .figure
            self.figure = {
                "marker": "fake_figure",
                "received_index": list(df.index),
                "layout_shapes": layout.get("shapes"),
            }

    monkeypatch.setattr(module, "SubplotsGraph", FakeSubplotsGraph)

    # Call the function under test
    fig = module.report_figure(pd.DataFrame())  # input ignored by our _calculate_report_data

    # Assertions on the returned "figure" sentinel
    assert isinstance(fig, dict)
    assert fig["marker"] == "fake_figure"

    # Ensure SubplotsGraph received the transformed DataFrame where first index is 'T0' (as set in function)
    received_index = fig["received_index"]
    assert received_index[0] == "T0"
    # After the in-function manipulation, first row's values should be zeros.
    # Check recorded df to inspect values
    recorded_df = recorded["df"]
    assert recorded_df.index.name == "date"
    # first row should be all zeros (numeric columns)
    first_row = recorded_df.iloc[0]
    for val in first_row:
        # They might be numeric zeros; compare equal to 0
        assert float(val) == 0.0

    # Layout shapes should reflect the fake _calculate_maximum outputs
    shapes = fig["layout_shapes"]
    assert isinstance(shapes, list)
    # There should be two rectangles with x0/x1 matching our fake_calc_maximum outputs
    rect1 = shapes[0]
    rect2 = shapes[1]
    assert rect1["x0"] == "2020-01-01" and rect1["x1"] == "2020-01-02"
    assert rect2["x0"] == "2020-01-02" and rect2["x1"] == "2020-01-03"

    # Validate that subplot layout has xaxis7 with showline True (i==7 branch)
    sub_graph_layout = recorded["sub_graph_layout"]
    assert "xaxis7" in sub_graph_layout
    assert sub_graph_layout["xaxis7"]["showline"] is True
    # And some other xaxis should have showline False
    assert sub_graph_layout["xaxis1"]["showline"] is False


def test_report_figure_calls_calculate_maximum_with_both_flags(monkeypatch, module):
    # This test ensures that _calculate_maximum is called twice: with exclusive False and True.
    fake_report_df = make_sample_report_df()
    monkeypatch.setattr(module, "_calculate_report_data", lambda df: fake_report_df)

    calls = []

    def recording_calc_maximum(df, exclusive=False):
        calls.append(bool(exclusive))
        # return distinct values so shapes still valid
        return ("S_EX" if exclusive else "S_MAIN", "E_EX" if exclusive else "E_MAIN")

    monkeypatch.setattr(module, "_calculate_maximum", recording_calc_maximum)

    # Dummy SubplotsGraph to avoid heavy plotting; just expose .figure
    class DummySubplotsGraph:
        def __init__(self, df, layout, sub_graph_data, subplots_kwargs, kind_map, sub_graph_layout):
            self.figure = ("ok",)

    monkeypatch.setattr(module, "SubplotsGraph", DummySubplotsGraph)

    result = module.report_figure(pd.DataFrame())
    assert result == ("ok",)

    # Verify that _calculate_maximum was called twice with exclusive False then True (order matters in function)
    assert calls == [False, True]
