import types
import builtins
from types import SimpleNamespace
import pytest

from rdagent.log.ui import web

# Helpers

def make_msg(tag, content):
    return SimpleNamespace(tag=tag, content=content)


def make_fake_self():
    # Minimal fake TraceWindow-like object with the attributes used by consume_msg
    called = {
        "rdl": [],
        "table": [],
        "plot": []
    }

    class SummaryC:
        def __init__(self):
            self.last_markdown = None

        def markdown(self, text):
            self.last_markdown = text

    class ChartC:
        def __init__(self):
            self.table_calls = []
            self.plot_calls = []

        def table(self, tbl):
            self.table_calls.append(tbl)

        def plotly_chart(self, fig):
            self.plot_calls.append(fig)

    class RDLWin:
        def __init__(self):
            self.consume_calls = []

        def consume_msg(self, msg):
            self.consume_calls.append(msg)

    fake = SimpleNamespace()
    fake.show_llm = False
    fake.show_common_logs = True
    fake.hypotheses = []
    fake.hypothesis_decisions = {}
    fake.summary_c = SummaryC()
    fake.results = []
    fake.chart_c = ChartC()
    fake.RDL_win = RDLWin()
    return fake


def test_llm_message_filtered_round_098():
    fake = make_fake_self()
    # show_llm False and tag contains 'llm_messages' -> early return, RDL_win.consume_msg not called
    fake.show_llm = False
    msg = make_msg("prefix llm_messages suffix", "anything")

    web.TraceWindow.consume_msg(fake, msg)

    assert fake.RDL_win.consume_calls == []


def test_common_log_filtered_round_098():
    fake = make_fake_self()
    fake.show_common_logs = False
    # content is a plain string -> early return
    msg = make_msg("some tag", "a plain log string")

    web.TraceWindow.consume_msg(fake, msg)

    assert fake.RDL_win.consume_calls == []


def test_dict_content_filtered_round_098():
    fake = make_fake_self()
    # content is a dict -> immediate return
    msg = make_msg("some tag", {"k": "v"})

    web.TraceWindow.consume_msg(fake, msg)

    assert fake.RDL_win.consume_calls == []


def test_hypothesis_and_feedback_round_098():
    fake = make_fake_self()
    # Create a lightweight hypothesis object expected by the UI code
    hyp = SimpleNamespace(hypothesis="H1", concise_reason="because", __repr__=lambda self: "H1")

    # 1) Send hypothesis generation message
    gen_msg = make_msg("session hypothesis generation", hyp)
    web.TraceWindow.consume_msg(fake, gen_msg)

    # hypothesis should have been appended and RDL_win called
    assert fake.hypotheses[-1] is hyp
    assert len(fake.RDL_win.consume_calls) == 1

    # 2) Send feedback message referencing the last hypothesis
    feedback_payload = SimpleNamespace(decision=True)
    fb_msg = make_msg("session ef.feedback", feedback_payload)
    web.TraceWindow.consume_msg(fake, fb_msg)

    # After feedback, the decision should be recorded for the last hypothesis
    assert fake.hypotheses[-1] in fake.hypothesis_decisions
    assert fake.hypothesis_decisions[fake.hypotheses[-1]] is True

    # summary_c.markdown should have been called and include hypothesis text and concise_reason
    assert fake.summary_c.last_markdown is not None
    assert "H1" in fake.summary_c.last_markdown
    assert "because" in fake.summary_c.last_markdown
    # For a True decision the UI inserts ':green[' in the formatted text
    assert ":green[" in fake.summary_c.last_markdown

    # RDL_win.consume_msg should have been called for the feedback as well
    assert len(fake.RDL_win.consume_calls) == 2


def test_results_table_and_plot_round_098(monkeypatch):
    fake = make_fake_self()

    # Prepare a deterministic first result (len==1 branch -> chart_c.table)
    first_result = {"metric": 0.1}
    msg1 = make_msg("abc ef.model runner result", SimpleNamespace(result=first_result))

    web.TraceWindow.consume_msg(fake, msg1)

    # After first single result, table should have been called with that result
    assert fake.results == [first_result]
    assert fake.chart_c.table_calls == [first_result]
    assert fake.chart_c.plot_calls == []

    # Now prepare second result (len>1 branch -> DataFrame -> px.line -> plotly_chart)
    second_result = {"metric": 0.2}
    msg2 = make_msg("abc ef.model runner result", SimpleNamespace(result=second_result))

    # Monkeypatch web.pd.DataFrame to return a fake dataframe with index and columns attributes
    class FakeDF:
        def __init__(self, results, index=None):
            # emulate pandas.DataFrame minimal interface used by the code
            # index used as x, columns used as y
            self.index = list(index) if index is not None else [1]
            # columns should be an iterable of column names; use keys of first result
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    self.columns = list(first.keys())
                else:
                    # fallback
                    self.columns = ["col"]
            else:
                self.columns = []

    def fake_dataframe(results, index=None):
        return FakeDF(results, index=index)

    monkeypatch.setattr(web, "pd", SimpleNamespace(DataFrame=fake_dataframe))

    # Monkeypatch px.line to validate parameters and return a fake figure
    def fake_px_line(df, x, y, markers=True):
        # Ensure the function receives the df and expected x/y coming from df
        assert x == df.index
        assert y == df.columns
        assert markers is True
        return "FIG_OBJECT"

    monkeypatch.setattr(web, "px", SimpleNamespace(line=fake_px_line))

    # Call with second msg
    web.TraceWindow.consume_msg(fake, msg2)

    # Results list should now contain both results
    assert fake.results == [first_result, second_result]

    # For the second call the code should have called px.line and then chart_c.plotly_chart
    assert fake.chart_c.plot_calls == ["FIG_OBJECT"]

    # RDL_win.consume_msg should have been called for both messages (plus any earlier invocations)
    assert len(fake.RDL_win.consume_calls) >= 2
