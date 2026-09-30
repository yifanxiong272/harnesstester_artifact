import sys
import types
import pandas as pd

# Prevent module-level argparse.parse_args from reading pytest CLI args
_old_argv = sys.argv[:]
sys.argv[:] = [sys.argv[0]]
try:
    import rdagent.log.ui.app as app
finally:
    # restore original argv so pytest and other modules function normally
    sys.argv[:] = _old_argv


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeSt:
    def __init__(self):
        self.calls = []
        self.last_table = None
        self.info_text = None

    def header(self, *args, **kwargs):
        self.calls.append(("header", args, kwargs))

    def subheader(self, *args, **kwargs):
        self.calls.append(("subheader", args, kwargs))

    def table(self, df):
        # store the DataFrame for inspection
        self.calls.append(("table", df))
        self.last_table = df

    def markdown(self, text):
        self.calls.append(("markdown", text))

    def columns(self, n):
        # return N context managers to be used in `with` blocks
        return [DummyContext() for _ in range(n)]

    def metric(self, label, value, delta=None, help=None):
        self.calls.append(("metric", label, value, delta, help))

    def expander(self, label):
        self.calls.append(("expander", label))
        return DummyContext()

    def info(self, text):
        self.calls.append(("info", text))
        self.info_text = text


class FB:
    def __init__(self, final_decision: bool):
        self.final_decision = final_decision


class Msg:
    def __init__(self, content):
        # content should be a list of FB-like objects
        self.content = content


class FakeState:
    def __init__(self, msgs, erounds):
        self.msgs = msgs
        self.erounds = erounds


def _patch_app(monkeypatch, fake_st, fake_state):
    # Patch the module-level names where analyze_task_completion resolves them
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "state", fake_state)


def test_analyze_no_data_round_006(monkeypatch):
    """When there is no message data, analyze_task_completion should call st.info with the no-data message."""
    fake_st = FakeSt()
    # Empty msgs leads to no completion_stats and the else branch (st.info)
    fake_state = FakeState(msgs={}, erounds={})

    _patch_app(monkeypatch, fake_st, fake_state)

    # Call the function under test
    app.analyze_task_completion()

    # Assert that info was called and had the expected message
    info_calls = [c for c in fake_st.calls if c[0] == "info"]
    assert len(info_calls) == 1, f"expected one st.info call, got: {fake_st.calls}"
    assert "No task completion data available." in info_calls[0][1]


def test_analyze_summary_round_006(monkeypatch):
    """Exercise the aggregate and per-loop summary paths, verify metrics and tables are produced with expected percentages."""
    fake_st = FakeSt()

    # Build feedback content for 3 tasks
    # Round 1: only task 0 passes
    r1 = [FB(True), FB(False), FB(False)]
    # Round 2: task 1 passes (cumulative now {0,1})
    r2 = [FB(False), FB(True), FB(False)]
    # Round 3: tasks 0 and 1 pass (no new ones) (cumulative remains {0,1})
    r3 = [FB(True), FB(True), FB(False)]

    # Construct messages expected shape: a list of Msg objects under key "evolving feedback"
    msgs = {
        1: {"evolving feedback": [Msg(r1), Msg(r2), Msg(r3)]}
    }
    # erounds shows max evolving round for loop 1 is 3
    erounds = {1: 3}
    fake_state = FakeState(msgs=msgs, erounds=erounds)

    _patch_app(monkeypatch, fake_st, fake_state)

    # Execute
    app.analyze_task_completion()

    # Assertions: aggregate subheader should have been emitted
    subheaders = [c for c in fake_st.calls if c[0] == "subheader"]
    assert any("Aggregate Completion Across All Loops" in args[0] for (_, args, _) in subheaders), f"subheader calls: {subheaders}"

    # Metrics: After Round 1 should be 1 of 3 -> 33%
    metric_calls = [c for c in fake_st.calls if c[0] == "metric"]
    labels = {call[1]: call for call in metric_calls}

    assert "After Round 1" in labels, f"metric calls missing After Round 1: {metric_calls}"
    assert labels["After Round 1"][2] == "33%"

    assert "After Round 3" in labels
    # After Round 3 cumulative across our single loop is 2/3 -> 67%
    assert labels["After Round 3"][2] == "67%"

    # Final Completion should also be 67%
    assert "Final Completion" in labels
    assert labels["Final Completion"][2] == "67%"

    # Expect at least two tables: one summary table and one per-loop table
    table_calls = [c for c in fake_st.calls if c[0] == "table"]
    assert len(table_calls) >= 2, f"expected at least two st.table calls, got: {table_calls}"

    # Inspect the last per-loop table (DataFrame) to ensure it contains rows for evolving rounds
    last_df = fake_st.last_table
    assert isinstance(last_df, pd.DataFrame)
    # There should be at least 1 row (we have 3 evolving rounds capped at min(11, max_round+1))
    assert len(last_df) >= 1
