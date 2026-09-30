import json
import types
import pytest

from rdagent.scenarios.qlib.proposal import factor_proposal as fp

# Fake/deterministic stand-ins for the real experiment and task classes.
# These are monkeypatched into the module under test so isinstance checks
# and attribute access behave predictably.
class FakeFactorTask:
    def __init__(self, factor_name, factor_description=None, factor_formulation=None, variables=None, **kwargs):
        self.factor_name = factor_name
        self.factor_description = factor_description
        self.factor_formulation = factor_formulation
        self.variables = variables

    def __repr__(self):
        return f"FakeFactorTask({self.factor_name!r})"

class FakeFactorExperiment:
    # Acts both as the FactorExperiment base and QlibFactorExperiment used by the code.
    def __init__(self, tasks=None, hypothesis=None, sub_tasks=None, **kwargs):
        # If sub_tasks explicitly provided, honor it (used for the empty based_experiments starter)
        if sub_tasks is not None:
            self.sub_tasks = sub_tasks
        else:
            # tasks passed in convert_response will be a list of FakeFactorTask objects
            # treat them as sub_tasks for duplication checks
            self.sub_tasks = list(tasks) if tasks is not None else []
        # tasks attribute is set/overwritten by convert_response at the end; initialize for clarity
        self.tasks = list(tasks) if tasks is not None else []
        self.hypothesis = hypothesis

    def __repr__(self):
        return f"FakeFactorExperiment(sub_tasks={self.sub_tasks!r})"

class FakeModelExperiment:
    pass

# Helper to produce a simple Trace-like object with a hist attribute
def make_trace_with_hist(hist_list):
    T = types.SimpleNamespace
    return T(hist=hist_list)


def _patch_fakes(monkeypatch):
    # Patch the symbols where the module resolves them
    monkeypatch.setattr(fp, 'FactorTask', FakeFactorTask)
    monkeypatch.setattr(fp, 'FactorExperiment', FakeFactorExperiment)
    monkeypatch.setattr(fp, 'QlibFactorExperiment', FakeFactorExperiment)
    monkeypatch.setattr(fp, 'QlibModelExperiment', FakeModelExperiment)


def test_no_duplicates_round_072(monkeypatch):
    """
    Scenario: response contains two distinct factors. The trace includes
    one FactorExperiment (with a different factor) and one QlibModelExperiment.
    Expectation: both factors from the response become tasks on the returned
    experiment because there are no duplicates.
    """
    _patch_fakes(monkeypatch)

    # Two distinct factors in response
    response_obj = {
        "factor_A": {
            "description": "Desc A",
            "formulation": "Form A",
            "variables": ["v1"]
        },
        "factor_B": {
            "description": "Desc B",
            "formulation": "Form B",
            "variables": ["v2"]
        }
    }
    response_json = json.dumps(response_obj)

    # Trace: contains a FakeFactorExperiment with a sub_task 'other' (shouldn't mark duplicates)
    other_sub = FakeFactorTask(factor_name='other')
    fe = FakeFactorExperiment(sub_tasks=[other_sub])
    me = FakeModelExperiment()

    trace = make_trace_with_hist([
        (fe, True),       # included and is a FactorExperiment
        (me, True),       # included but is a QlibModelExperiment and should be skipped in duplicate scanning
        (fe, False)       # excluded by the boolean flag
    ])

    # hypothesis is unused for logic here; pass a simple sentinel
    hypothesis = object()

    # Call the method as an unbound function (no special init required for self)
    exp = fp.QlibFactorHypothesis2Experiment.convert_response(object(), response_json, hypothesis, trace)

    # Verify that tasks were created for both factors and preserved
    assert isinstance(exp, FakeFactorExperiment)
    assert len(exp.tasks) == 2
    names = [t.factor_name for t in exp.tasks]
    assert set(names) == {"factor_A", "factor_B"}

    # Verify FactorTask fields are preserved from the JSON
    a = next(t for t in exp.tasks if t.factor_name == "factor_A")
    assert a.factor_description == "Desc A"
    assert a.factor_formulation == "Form A"
    assert a.variables == ["v1"]

    # The first based_experiment added by code should have empty sub_tasks as constructed
    # Constructed inside convert_response as QlibFactorExperiment(sub_tasks=[])
    # Ensure that behaviour took place by reconstructing the logic and checking expectations
    # (We can't directly access local based_experiments variable, but we rely on consistent behaviour
    # that no duplicates were removed.)


def test_with_duplicates_and_model_skip_round_072(monkeypatch):
    """
    Scenario: response contains a factor 'dup' and 'keep'. The trace's based_experiments
    include a FactorExperiment with a sub_task named 'dup' and also a QlibModelExperiment.
    Expectation: 'dup' is detected as duplicate and filtered out; only 'keep' remains.
    """
    _patch_fakes(monkeypatch)

    response_obj = {
        "dup": {
            "description": "Desc D",
            "formulation": "Form D",
            "variables": []
        },
        "keep": {
            "description": "Desc K",
            "formulation": "Form K",
            "variables": [1, 2]
        }
    }
    response_json = json.dumps(response_obj)

    # Prepare based_experiments such that one has a sub_task with factor_name 'dup'
    dup_sub = FakeFactorTask(factor_name='dup')
    based_fe_with_dup = FakeFactorExperiment(sub_tasks=[dup_sub])

    # Also include a model experiment that must be skipped by the duplicate-check loop
    model_ex = FakeModelExperiment()

    trace = make_trace_with_hist([
        (based_fe_with_dup, True),
        (model_ex, True),
    ])

    hypothesis = object()

    exp = fp.QlibFactorHypothesis2Experiment.convert_response(object(), response_json, hypothesis, trace)

    # Only 'keep' should survive de-duplication
    assert isinstance(exp, FakeFactorExperiment)
    names = [t.factor_name for t in exp.tasks]
    assert names == ["keep"]

    # Ensure the kept task preserves fields
    kept = exp.tasks[0]
    assert kept.factor_description == "Desc K"
    assert kept.variables == [1, 2]
