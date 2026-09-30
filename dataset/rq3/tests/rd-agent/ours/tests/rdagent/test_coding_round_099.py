import importlib
import contextlib
import pytest

loop_mod = importlib.import_module("rdagent.scenarios.data_science.loop")

# Helper test doubles
class DummyLogger:
    def __init__(self):
        self.last_tag = None
        self.logged_object = None

    @contextlib.contextmanager
    def tag(self, tag):
        # emulate the context manager used in the code under test
        self.last_tag = tag
        yield None

    def log_object(self, obj):
        self.logged_object = obj


class FakeCoder:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def develop(self, exp):
        # mark exp to prove that this coder ran and return the experiment
        exp.last_developed_by = self.name
        self.calls.append(exp)
        return exp


class DummyTaskBase:
    pass


class DataLoaderTask(DummyTaskBase):
    pass


class FeatureTask(DummyTaskBase):
    pass


class ModelTask(DummyTaskBase):
    pass


class EnsembleTask(DummyTaskBase):
    pass


class WorkflowTask(DummyTaskBase):
    pass


class PipelineTask(DummyTaskBase):
    pass


class FakeHypothesis:
    def __init__(self, component):
        self.component = component


class FakeExp:
    def __init__(self, pending_tasks_list, component_name="unknown"):
        # pending_tasks_list should be an iterable of lists of tasks
        self.pending_tasks_list = pending_tasks_list
        self.sub_tasks = []
        self.hypothesis = FakeHypothesis(component_name)
        self.last_developed_by = None


class FakeSelf:
    def __init__(self, logger, coders):
        # coders: dict of coder name to FakeCoder
        self.logger = logger
        # place coder attributes on self matching names used in function
        self.data_loader_coder = coders.get("data_loader")
        self.feature_coder = coders.get("feature")
        self.model_coder = coders.get("model")
        self.ensemble_coder = coders.get("ensemble")
        self.workflow_coder = coders.get("workflow")
        self.pipeline_coder = coders.get("pipeline")


# Utility to inject our dummy Task classes and logger into the module under test
def prepare_module_with_dummies(monkeypatch):
    monkeypatch.setattr(loop_mod, "DataLoaderTask", DataLoaderTask, raising=False)
    monkeypatch.setattr(loop_mod, "FeatureTask", FeatureTask, raising=False)
    monkeypatch.setattr(loop_mod, "ModelTask", ModelTask, raising=False)
    monkeypatch.setattr(loop_mod, "EnsembleTask", EnsembleTask, raising=False)
    monkeypatch.setattr(loop_mod, "WorkflowTask", WorkflowTask, raising=False)
    monkeypatch.setattr(loop_mod, "PipelineTask", PipelineTask, raising=False)
    fake_logger = DummyLogger()
    monkeypatch.setattr(loop_mod, "logger", fake_logger, raising=False)
    return fake_logger


# Tests for each branch, asserting coder selection, clearing of sub_tasks, and logger call

def test_data_loader_branch_round_099(monkeypatch):
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    exp = FakeExp(pending_tasks_list=[[DataLoaderTask()]])

    returned = loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert returned is exp
    assert exp.last_developed_by == "data_loader"
    assert exp.sub_tasks == []
    assert fake_logger.logged_object is exp
    assert fake_logger.last_tag == f"{exp.sub_tasks[:] and exp.sub_tasks[0].__class__.__name__ or 'None'}" or fake_logger.last_tag is None


def test_feature_branch_round_099(monkeypatch):
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    exp = FakeExp(pending_tasks_list=[[FeatureTask()]])

    returned = loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert returned is exp
    assert exp.last_developed_by == "feature"
    assert exp.sub_tasks == []
    assert fake_logger.logged_object is exp


def test_model_branch_round_099(monkeypatch):
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    exp = FakeExp(pending_tasks_list=[[ModelTask()]])

    returned = loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert returned is exp
    assert exp.last_developed_by == "model"
    assert exp.sub_tasks == []
    assert fake_logger.logged_object is exp


def test_ensemble_branch_round_099(monkeypatch):
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    exp = FakeExp(pending_tasks_list=[[EnsembleTask()]])

    returned = loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert returned is exp
    assert exp.last_developed_by == "ensemble"
    assert exp.sub_tasks == []
    assert fake_logger.logged_object is exp


def test_workflow_branch_round_099(monkeypatch):
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    exp = FakeExp(pending_tasks_list=[[WorkflowTask()]])

    returned = loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert returned is exp
    assert exp.last_developed_by == "workflow"
    assert exp.sub_tasks == []
    assert fake_logger.logged_object is exp


def test_pipeline_branch_round_099(monkeypatch):
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    exp = FakeExp(pending_tasks_list=[[PipelineTask()]])

    returned = loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert returned is exp
    assert exp.last_developed_by == "pipeline"
    assert exp.sub_tasks == []
    assert fake_logger.logged_object is exp


def test_unsupported_component_raises_round_099(monkeypatch):
    # When the subtask is not one of the supported Task types, a NotImplementedError is raised
    fake_logger = prepare_module_with_dummies(monkeypatch)

    coders = {
        "data_loader": FakeCoder("data_loader"),
        "feature": FakeCoder("feature"),
        "model": FakeCoder("model"),
        "ensemble": FakeCoder("ensemble"),
        "workflow": FakeCoder("workflow"),
        "pipeline": FakeCoder("pipeline"),
    }
    fake_self = FakeSelf(fake_logger, coders)

    class UnknownTask:
        pass

    exp = FakeExp(pending_tasks_list=[[UnknownTask()]], component_name="mystery_component")

    with pytest.raises(NotImplementedError) as excinfo:
        loop_mod.DataScienceRDLoop.coding(fake_self, {"direct_exp_gen": exp})

    assert "Unsupported component in DataScienceRDLoop" in str(excinfo.value)
    assert "mystery_component" in str(excinfo.value)
