import sys
# Protect module import from argparse picking up pytest's argv
_orig_argv = sys.argv[:]
sys.argv = ["rd-agent-test"]

import rdagent.log.ui.app as app

# restore argv so pytest behavior is not affected after import
sys.argv = _orig_argv


class _Dummy:
    """Tiny object whose attributes form its __dict__, used as Hypothesis stand-ins."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _capture_markdown(monkeypatch):
    """Patch app.st.markdown to capture the last HTML passed and return a list for inspection."""
    container = {"calls": []}

    def fake_markdown(html, unsafe_allow_html=False):
        container["calls"].append({"html": html, "unsafe": unsafe_allow_html})

    # Patch the markdown function used in the module under test
    monkeypatch.setattr(app.st, "markdown", fake_markdown)
    return container


def test_display_hypotheses_success_only_round_064(monkeypatch):
    """Covers: success_only True path, concise_observation/concise_justification swap, dropping reason/concise_reason,
    dropping columns where all values are None, and the styling (green for chosen).
    """
    cap = _capture_markdown(monkeypatch)

    # Hypothesis 1 will be included (decision True). Hypothesis 2 exists but will be filtered out by success_only.
    h1 = _Dummy(
        hypothesis="H1 text",
        concise_justification="just1",
        concise_observation="obs1",
        reason="a reason to drop",
        concise_reason="short reason to drop",
        empty_col=None,  # this column is None for every included row -> should be dropped
    )
    h2 = _Dummy(hypothesis="H2 text", concise_justification="j2")

    hypotheses = {1: h1, 2: h2}
    decisions = {1: True, 2: False}

    # Call function under test
    app.display_hypotheses(hypotheses, decisions, success_only=True)

    # Ensure markdown was invoked once
    assert cap["calls"], "st.markdown was not called"
    html = cap["calls"][0]["html"]

    # Dropped columns should not appear in the produced HTML
    assert "reason" not in html
    assert "concise_reason" not in html
    assert "empty_col" not in html

    # The chosen (decision True) row should have green styling applied
    assert "color: green" in html

    # There should be bold styling for the hypothesis column label (humanized name)
    # and italic styling for other columns
    assert "font-weight: bold" in html or "font-weight:bold" in html
    assert "font-style: italic" in html


def test_display_hypotheses_mixed_decisions_and_columns_round_064(monkeypatch):
    """Covers: success_only False path (keeps all hypotheses), branch where concise_* swap is NOT executed,
    column retained when not all-None, and style_rows returns empty style for non-chosen rows.
    """
    cap = _capture_markdown(monkeypatch)

    # Create two hypotheses (both included because success_only=False)
    # Only concise_justification is provided (no concise_observation) to avoid the swap branch here.
    h1 = _Dummy(hypothesis="H1 text", concise_justification="just1", mixed_col=None)
    h2 = _Dummy(hypothesis="H2 text", concise_justification="just2", mixed_col="present")

    hypotheses = {1: h1, 2: h2}
    decisions = {1: True, 2: False}

    app.display_hypotheses(hypotheses, decisions, success_only=False)

    assert cap["calls"], "st.markdown was not called"
    html = cap["calls"][0]["html"]

    # The mixed_col should be kept because not all values are None across rows
    assert "mixed_col" in html

    # Both styles should be present overall: chosen row (green) and column styling (italic/bold)
    assert "color: green" in html
    assert ("font-style: italic" in html) or ("font-weight: bold" in html)

    # Because concise_observation wasn't present, a swap should not have occurred that would introduce
    # the concise_observation name content in unexpected places; we assert that the literal string
    # 'concise_observation' is not unexpectedly introduced (it may still appear as cell content if present).
    # In this test we never added concise_observation, so it should not appear as a column name.
    assert "concise_observation" not in html
