# file: rdagent/log/ui/app.py:508-547
# asked: {"lines": [508, 509, 510, 511, 512, 513, 514, 515, 516, 518, 519, 520, 522, 523, 524, 525, 526, 528, 529, 530, 531, 532, 533, 534, 535, 537, 538, 539, 540, 542, 543, 544, 545, 546, 547], "branches": [[509, 510], [509, 528], [512, 513], [512, 514], [515, 0], [515, 516], [523, 515], [523, 524], [524, 525], [524, 526], [528, 0], [528, 529], [531, 532], [531, 533], [534, 0], [534, 535], [543, 544], [543, 547], [544, 545], [544, 546]]}
# gained: {"lines": [508, 509, 510, 511, 512, 514, 515, 516, 518, 519, 520, 522, 523, 524, 525, 526, 528, 529, 530, 531, 532, 533, 534, 535, 537, 538, 539, 540, 542, 543, 544, 545, 546, 547], "branches": [[509, 510], [509, 528], [512, 514], [515, 0], [515, 516], [523, 524], [524, 525], [524, 526], [528, 529], [531, 532], [534, 0], [534, 535], [543, 544], [544, 545], [544, 546]]}

import importlib
import argparse
from types import SimpleNamespace
import pytest

def _make_fake_st():
    class FakeTab:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeST:
        def __init__(self):
            self.markdowns = []
            self.latexes = []
            self.tabs_called_with = None

        def markdown(self, txt):
            self.markdowns.append(str(txt))

        def latex(self, txt):
            self.latexes.append(str(txt))

        def tabs(self, names):
            self.tabs_called_with = list(names)
            return [FakeTab() for _ in names]

    return FakeST()

def _patch_argparse_parse_args(monkeypatch):
    def fake_parse_args(self):
        return SimpleNamespace(log_dir=None, debug=False)
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", fake_parse_args, raising=True)

def test_tasks_window_factor_branch_with_variables(monkeypatch):
    # Prevent module-level argparse from exiting on import
    _patch_argparse_parse_args(monkeypatch)

    # Import the module under test after patching argparse
    import rdagent.log.ui.app as app
    importlib.reload(app)

    # Prepare fake streamlit and inject
    fake_st = _make_fake_st()
    monkeypatch.setattr(app, "st", fake_st)

    # tabs_hint recorder
    called = {"tabs_hint": False}
    def fake_tabs_hint():
        called["tabs_hint"] = True
    monkeypatch.setattr(app, "tabs_hint", fake_tabs_hint)

    # Fake FactorTask class and patch into module for isinstance checks
    class FakeFactorTask:
        def __init__(self, factor_name, factor_description, factor_formulation, variables):
            self.factor_name = factor_name
            self.factor_description = factor_description
            self.factor_formulation = factor_formulation
            self.variables = variables

    monkeypatch.setattr(app, "FactorTask", FakeFactorTask)

    # Create tasks with short names to avoid triggering tabs_hint
    t1 = FakeFactorTask("A", "desc A", "form A", {"x": "var x"})
    t2 = FakeFactorTask("B", "desc B", "form B", {"y": "var y"})
    app.tasks_window([t1, t2])

    # Assertions
    assert any("Factor Tasks" in m for m in fake_st.markdowns), "Factor header missing"
    assert any("Description" in m and "desc A" in m for m in fake_st.markdowns)
    assert any("Description" in m and "desc B" in m for m in fake_st.markdowns)
    assert fake_st.latexes.count("Formulation") == 2
    assert "form A" in fake_st.latexes
    assert "form B" in fake_st.latexes
    assert any("| $x$ | var x |" in m for m in fake_st.markdowns), "Variable x not in markdown"
    assert any("| $y$ | var y |" in m for m in fake_st.markdowns), "Variable y not in markdown"
    assert called["tabs_hint"] is False

def test_tasks_window_model_branch_triggers_tabs_hint_and_train_params(monkeypatch):
    # Prevent module-level argparse from exiting on import
    _patch_argparse_parse_args(monkeypatch)

    # Import and reload module
    import rdagent.log.ui.app as app
    importlib.reload(app)

    # Prepare fake streamlit and tabs hint recorder
    fake_st = _make_fake_st()
    monkeypatch.setattr(app, "st", fake_st)

    called = {"tabs_hint": False}
    def fake_tabs_hint():
        called["tabs_hint"] = True
    monkeypatch.setattr(app, "tabs_hint", fake_tabs_hint)

    # Fake ModelTask and patch into module for isinstance checks
    class FakeModelTask:
        def __init__(self, name, model_type, description, formulation, variables, training_hyperparameters):
            self.name = name
            self.model_type = model_type
            self.description = description
            self.formulation = formulation
            self.variables = variables
            self.training_hyperparameters = training_hyperparameters

    monkeypatch.setattr(app, "ModelTask", FakeModelTask)

    # Create names whose combined length exceeds 100 to trigger tabs_hint
    long_name = "N" * 60
    long_name2 = "M" * 60
    m1 = FakeModelTask(
        name=long_name,
        model_type="Type1",
        description="Model desc 1",
        formulation="form1",
        variables={"a": "va"},
        training_hyperparameters="epochs=10"
    )
    m2 = FakeModelTask(
        name=long_name2,
        model_type="Type2",
        description="Model desc 2",
        formulation="form2",
        variables={"b": "vb"},
        training_hyperparameters="epochs=20"
    )

    app.tasks_window([m1, m2])

    # Assertions
    assert called["tabs_hint"] is True
    assert any("Model Tasks" in m for m in fake_st.markdowns), "Model header missing"
    assert any("Model Type" in m and "Type1" in m for m in fake_st.markdowns)
    assert any("Description" in m and "Model desc 1" in m for m in fake_st.markdowns)
    assert "Formulation" in fake_st.latexes
    assert "form1" in fake_st.latexes or "form2" in fake_st.latexes
    assert any("| $a$ | va |" in m for m in fake_st.markdowns)
    assert any("| $b$ | vb |" in m for m in fake_st.markdowns)
    assert any("Train Para" in m and "epochs=10" in m for m in fake_st.markdowns)
    assert any("Train Para" in m and "epochs=20" in m for m in fake_st.markdowns)
