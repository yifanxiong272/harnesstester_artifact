import importlib
import argparse
import types

import pytest

# Tests for rdagent.log.ui.app.tasks_window
# All test functions and file name end with _round_046 as required.

class DummyTab:
    def __init__(self, idx, record_list):
        self.idx = idx
        self.record_list = record_list

    def __enter__(self):
        # record that this tab was entered
        self.record_list.append(f"enter-{self.idx}")
        return self

    def __exit__(self, exc_type, exc, tb):
        # record that this tab was exited
        self.record_list.append(f"exit-{self.idx}")
        return False


class DummySt:
    def __init__(self):
        self.markdown_calls = []
        self.latex_calls = []
        self._context_calls = []

    def markdown(self, txt):
        # store textual markdown calls for assertions
        self.markdown_calls.append(str(txt))

    def latex(self, txt):
        # store latex calls
        self.latex_calls.append(str(txt))

    def tabs(self, tnames):
        # return a list of context-manager-like objects (one per tab name)
        tabs = []
        for i, _ in enumerate(tnames):
            tabs.append(DummyTab(i, self._context_calls))
        return tabs


class DummyFactorTask:
    def __init__(self, factor_name, factor_description, factor_formulation, variables):
        self.factor_name = factor_name
        self.factor_description = factor_description
        self.factor_formulation = factor_formulation
        self.variables = variables


class DummyModelTask:
    def __init__(self, name, model_type, description, formulation, variables, training_hyperparameters):
        self.name = name
        self.model_type = model_type
        self.description = description
        self.formulation = formulation
        self.variables = variables
        self.training_hyperparameters = training_hyperparameters


def _prepare_app_monkeypatch(monkeypatch):
    """Monkeypatch argparse.parse_args to avoid SystemExit on import, then import the app module and monkeypatch st, FactorTask, ModelTask, tabs_hint.
    Returns the module and the DummySt instance for inspection."""
    # Prevent argparse from consuming pytest CLI args during import
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: argparse.Namespace(log_dir=None, debug=False))

    app = importlib.import_module("rdagent.log.ui.app")

    dummy_st = DummySt()
    # Patch the symbols where tasks_window resolves them
    monkeypatch.setattr(app, "st", dummy_st)
    monkeypatch.setattr(app, "FactorTask", DummyFactorTask)
    monkeypatch.setattr(app, "ModelTask", DummyModelTask)

    # Provide a tabs_hint recorder
    tabs_hint_called = {"count": 0}

    def tabs_hint():
        tabs_hint_called["count"] += 1

    monkeypatch.setattr(app, "tabs_hint", tabs_hint)

    return app, dummy_st, tabs_hint_called


def test_tasks_window_factor_long_names_round_046(monkeypatch):
    app, dummy_st, tabs_hint_called = _prepare_app_monkeypatch(monkeypatch)

    # Create a FactorTask whose name length alone exceeds 100 to trigger tabs_hint branch
    long_name = "a" * 120
    variables = {"x": "desc_x", "y": "desc_y"}
    ft = DummyFactorTask(long_name, "some description", "x = y + 1", variables)

    # Call the function under test
    app.tasks_window([ft])

    # Assertions (oracle):
    # - tabs_hint should be called because total name length > 100
    assert tabs_hint_called["count"] == 1

    # - st.markdown should have been called for the Factor Tasks header
    assert any("Factor Tasks" in m for m in dummy_st.markdown_calls), "expected Factor Tasks header"

    # - description markdown should be recorded
    assert any("Description" in m for m in dummy_st.markdown_calls), "expected description to be markdowned"

    # - latex calls: one for "Formulation" and one for the factor formulation
    assert "Formulation" in dummy_st.latex_calls[0]
    assert "x = y + 1" in dummy_st.latex_calls[1]

    # - variables table should include each variable name and description
    table_call = "\n".join(dummy_st.markdown_calls)
    assert "$x$" in table_call and "desc_x" in table_call
    assert "$y$" in table_call and "desc_y" in table_call


def test_tasks_window_model_no_vars_round_046(monkeypatch):
    app, dummy_st, tabs_hint_called = _prepare_app_monkeypatch(monkeypatch)

    # Create a ModelTask with empty variables dict (falsy) to exercise the branch that skips variable table
    long_name = "m" * 110
    mt = DummyModelTask(long_name, "SomeModelType", "model desc", "f(z)=z^2", {}, {"lr": 0.01})

    # Call tasks_window
    app.tasks_window([mt])

    # tabs_hint should have been called once (long name)
    assert tabs_hint_called["count"] == 1

    # Model header should be present
    assert any("Model Tasks" in m for m in dummy_st.markdown_calls), "expected Model Tasks header"

    # Model type and description should have been markdowned
    assert any("Model Type" in m for m in dummy_st.markdown_calls)
    assert any("Description" in m for m in dummy_st.markdown_calls)

    # latex calls should include "Formulation" and the model formulation
    assert "Formulation" in dummy_st.latex_calls[0]
    assert "f(z)=z^2" in dummy_st.latex_calls[1]

    # Because variables is empty (falsy), the variable-table markdown should NOT contain any variable rows
    combined = "\n".join(dummy_st.markdown_calls)
    # Ensure no variable rows are present
    assert "$z$" not in combined and "z_desc" not in combined

    # Training hyperparameters must be printed at the end
    assert any("Train Para" in m and "{'lr': 0.01}" in m for m in dummy_st.markdown_calls), "expected training hyperparameters printed"


def test_tasks_window_model_with_vars_round_046(monkeypatch):
    app, dummy_st, tabs_hint_called = _prepare_app_monkeypatch(monkeypatch)

    # Create a ModelTask with a small name and a non-empty variables dict to exercise the variable-table branch
    mt = DummyModelTask("nm", "T", "desc", "g(x)", {"z": "z_desc"}, {"batch": 32})

    # Call tasks_window
    app.tasks_window([mt])

    # tabs_hint should NOT be required here because name lengths are small
    assert tabs_hint_called["count"] == 0

    # The variable-table should include the variable z and its description
    combined = "\n".join(dummy_st.markdown_calls)
    assert "$z$" in combined and "z_desc" in combined

    # Training hyperparameters must still be printed
    assert any("Train Para" in m and "{'batch': 32}" in m for m in dummy_st.markdown_calls)
