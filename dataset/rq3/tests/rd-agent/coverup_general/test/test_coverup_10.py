# file: rdagent/log/ui/ds_summary.py:71-198
# asked: {"lines": [71, 72, 73, 74, 75, 76, 77, 79, 80, 83, 85, 86, 87, 88, 90, 91, 92, 93, 94, 96, 97, 98, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 121, 122, 124, 126, 128, 129, 130, 132, 133, 134, 135, 137, 138, 140, 141, 143, 144, 145, 146, 148, 150, 153, 154, 155, 156, 157, 158, 159, 160, 161, 163, 164, 165, 168, 169, 171, 174, 175, 178, 179, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 194, 197, 198], "branches": [[73, 74], [73, 75], [75, 76], [75, 77], [85, 86], [85, 90], [86, 85], [86, 87], [92, 93], [92, 98], [113, 114], [113, 124], [114, 115], [114, 116], [116, 117], [116, 118], [118, 119], [118, 121], [126, 128], [126, 143], [132, 133], [132, 134], [134, 135], [134, 137]]}
# gained: {"lines": [71, 72, 73, 74, 75, 76, 79, 80, 83, 85, 86, 87, 88, 90, 91, 92, 93, 94, 96, 97, 98, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 113, 124, 126, 128, 129, 130, 132, 134, 135, 137, 138, 140, 141, 143, 144, 145, 146, 148, 150, 153, 154, 155, 156, 157, 158, 159, 160, 161, 163, 164, 165, 168, 169, 171, 174, 175, 178, 179, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 194, 197, 198], "branches": [[73, 74], [73, 75], [75, 76], [85, 86], [85, 90], [86, 87], [92, 93], [92, 98], [113, 124], [126, 128], [126, 143], [132, 134], [134, 135], [134, 137]]}

import pandas as pd
import types
import pytest

import rdagent.log.ui.ds_summary as ds_summary


class FigStub:
    def __init__(self):
        self.vlines = []
        self.annotations = []

    def update_layout(self, **kwargs):
        self.layout = kwargs

    def add_vline(self, **kwargs):
        self.vlines.append(kwargs)

    def add_annotation(self, **kwargs):
        self.annotations.append(kwargs)


class ColumnStub:
    def __init__(self, select_value="ALL", toggle_value=False):
        self._select_value = select_value
        self._toggle_value = toggle_value

    def selectbox(self, *args, **kwargs):
        return self._select_value

    def toggle(self, *args, **kwargs):
        return self._toggle_value

    # Support context manager used in "with stat_win_left:" etc.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class StreamlitStub:
    def __init__(self, select_value="ALL", toggle_value=False, recorder=None):
        self._select_value = select_value
        self._toggle_value = toggle_value
        self.calls = recorder if recorder is not None else {}
        # emulate column_config namespace used in code
        self.column_config = types.SimpleNamespace(CheckboxColumn=lambda *a, **k: ("CheckboxColumn", a, k))

    def multiselect(self, *args, **kwargs):
        return ds_summary.state.log_folders

    def warning(self, msg):
        self.calls.setdefault("warning", []).append(msg)

    def columns(self, n):
        return ColumnStub(self._select_value, self._toggle_value), ColumnStub(self._select_value, self._toggle_value)

    def data_editor(self, df, *args, **kwargs):
        self.calls.setdefault("data_editor", []).append(df.copy())
        return df

    def markdown(self, *args, **kwargs):
        self.calls.setdefault("markdown", []).append(args)

    def text(self, txt):
        self.calls.setdefault("text", []).append(txt)

    def dataframe(self, df):
        self.calls.setdefault("dataframe", []).append(df.copy())

    def plotly_chart(self, fig, use_container_width=None):
        self.calls.setdefault("plotly_chart", []).append(fig)

    def subheader(self, *args, **kwargs):
        self.calls.setdefault("subheader", []).append((args, kwargs))


@pytest.fixture(autouse=True)
def restore_path_exists(monkeypatch):
    # placeholder to allow monkeypatching Path.exists in tests safely
    yield


def make_summary_and_df():
    df = pd.DataFrame(
        {
            "Valid Improve": [0.1, 0.3, 0.2, 0.0],
            "Test Improve": [0.05, 0.07, 0.02, 0.01],
            "Submit Merge": [0.0, 0.0, 0.0, 0.0],
            "Merge Sota": [0.0, 0.0, 0.0, 0.0],
            "SOTA Exp Score (valid, to_submit)": [1.0, 2.5, 5.0, 0.1],
            "Competition": ["compA", "compA", "compB", "compB"],
            "Total Loops": [10, 20, 30, 40],
        },
        index=["t1", "t2", "t3", "t4"],
    )
    summary = {"meta1": {"a": 1}, "meta2": {"b": 2}}
    return summary, df


def make_stat_df():
    rows = []
    for i in range(7):
        rows.append([f"name{i}", float(i + 0.5)])
    stat_df = pd.DataFrame(rows)
    return stat_df


def setup_common_mocks(monkeypatch, st_stub, summary_df_pair, stat_df, fig_stub, metric_dir_map=None):
    monkeypatch.setattr(ds_summary, "st", st_stub)
    monkeypatch.setattr(ds_summary, "state", types.SimpleNamespace(log_folders=["/path/amltX/run", "/another/epY/run"]))
    # Path.exists should be a method; patch to always return False to trigger warning branch
    monkeypatch.setattr(ds_summary.Path, "exists", lambda self: False)
    monkeypatch.setattr(ds_summary, "get_summary_df", lambda lf: summary_df_pair)
    monkeypatch.setattr(ds_summary, "percent_df", lambda df: df)
    captured = {}

    def _get_statistics_df(df):
        captured["df"] = df.copy()
        return stat_df

    monkeypatch.setattr(ds_summary, "get_statistics_df", _get_statistics_df)
    called = {}
    monkeypatch.setattr(ds_summary, "curves_win", lambda summary: called.setdefault("summary", summary))
    monkeypatch.setattr(ds_summary.px, "histogram", lambda *a, **k: fig_stub)
    if metric_dir_map is None:
        metric_dir_map = {"compA": True, "compB": False}

    def _get_metric_direction(comp):
        # accept Series/Index by taking first element
        if isinstance(comp, (pd.Series, pd.Index)):
            if len(comp) == 0:
                return True
            comp_val = comp.iloc[0]
        elif isinstance(comp, (list, tuple)):
            comp_val = comp[0]
        else:
            comp_val = comp
        return metric_dir_map.get(comp_val, True)

    monkeypatch.setattr(ds_summary, "get_metric_direction", _get_metric_direction)
    return captured, called


def test_all_summarize_win_toggle_false(monkeypatch):
    summary_df_pair = make_summary_and_df()
    stat_df = make_stat_df()
    fig_stub = FigStub()
    st_calls = {}
    st_stub = StreamlitStub(select_value="ALL", toggle_value=False, recorder=st_calls)

    captured, called = setup_common_mocks(monkeypatch, st_stub, summary_df_pair, stat_df, fig_stub)

    ds_summary.all_summarize_win()

    # Warnings for each folder since Path.exists returns False
    assert "warning" in st_calls and len(st_calls["warning"]) == len(ds_summary.state.log_folders)
    # data_editor was called with a DataFrame
    assert "data_editor" in st_calls and isinstance(st_calls["data_editor"][0], pd.DataFrame)
    # get_statistics_df was invoked and captured a DataFrame
    assert "df" in captured
    # Since selectbox == "ALL", at least one row should be selected before statistics
    assert captured["df"].shape[0] >= 1
    # plotly chart was called with our fig stub
    assert "plotly_chart" in st_calls and st_calls["plotly_chart"][0] is fig_stub
    # curves_win was called with a summary dict
    assert "summary" in called and isinstance(called["summary"], dict)


def test_all_summarize_win_toggle_true_both_directions(monkeypatch):
    summary, df = make_summary_and_df()
    stat_df = make_stat_df()
    fig_stub = FigStub()
    st_calls = {}
    st_stub = StreamlitStub(select_value="ALL", toggle_value=True, recorder=st_calls)

    metric_map = {"compA": True, "compB": False}

    captured, called = setup_common_mocks(monkeypatch, st_stub, (summary, df), stat_df, fig_stub, metric_dir_map=metric_map)

    ds_summary.all_summarize_win()

    assert "df" in captured
    filtered_df = captured["df"]
    # After selecting best per competition there should be at least one row per competition
    assert filtered_df.shape[0] >= 2
    # Ensure compA row chosen has SOTA Exp Score 2.5 (max) and compB row chosen has 0.1 (min)
    compA_vals = filtered_df.loc[filtered_df["Competition"] == "compA", "SOTA Exp Score (valid, to_submit)"].tolist()
    compB_vals = filtered_df.loc[filtered_df["Competition"] == "compB", "SOTA Exp Score (valid, to_submit)"].tolist()
    assert any(abs(v - 2.5) < 1e-8 for v in compA_vals)
    assert any(abs(v - 0.1) < 1e-8 for v in compB_vals)
    assert "summary" in called and isinstance(called["summary"], dict)
