import builtins
import types
from pathlib import Path
import pandas as pd
import importlib
import pytest

# Import the module under test
fr = importlib.import_module("rdagent.scenarios.qlib.developer.factor_runner")

# Helper to call the possibly-decorated develop implementation bypassing cache wrapper if present
def _call_develop_impl(self_obj, exp):
    func = getattr(fr.QlibFactorRunner.develop, "__wrapped__", fr.QlibFactorRunner.develop)
    return func(self_obj, exp)


class DummyWorkspace:
    def __init__(self, workspace_path, execute_return=("ok_result", "ok_stdout")):
        self.workspace_path = Path(workspace_path)
        self._execute_return = execute_return
        self.injected = {}
        self.execute_called_with = None

    def inject_files(self, **kwargs):
        self.injected.update(kwargs)

    def execute(self, qlib_config_name=None, run_env=None):
        # capture what was passed for assertions
        self.execute_called_with = {"qlib_config_name": qlib_config_name, "run_env": run_env}
        return self._execute_return


class DummyFactorExp:
    def __init__(self, based_experiments=None, workspace_path="/tmp", result=None):
        self.based_experiments = based_experiments or []
        self.experiment_workspace = DummyWorkspace(workspace_path)
        self.result = result
        self.stdout = None
        # for compatibility: sub_workspace_list & sub_tasks may be set externally for model exps
        self.sub_workspace_list = []
        self.sub_tasks = []


class DummyModelExp:
    def __init__(self, sub_workspace_list, sub_tasks):
        self.sub_workspace_list = sub_workspace_list
        self.sub_tasks = sub_tasks


class DummySubWorkspace:
    def __init__(self, file_dict):
        self.file_dict = file_dict


class DummySubTask:
    def __init__(self, model_type=None, training_hyperparameters=None):
        self.model_type = model_type
        self.training_hyperparameters = training_hyperparameters or {}


# Patch module-level symbols used by develop; tests will monkeypatch specific behaviors per test
@pytest.fixture(autouse=True)
def patch_module_defaults(monkeypatch, tmp_path):
    # Ensure RD_AGENT_SETTINGS has predictable initial_fator_library_size
    class DummySettings:
        initial_fator_library_size = 5

    monkeypatch.setattr(fr, "RD_AGENT_SETTINGS", DummySettings)

    # Replace the Qlib* classes in the module to allow isinstance checks to work with our dummies
    monkeypatch.setattr(fr, "QlibFactorExperiment", DummyFactorExp)
    monkeypatch.setattr(fr, "QlibModelExperiment", DummyModelExp)

    # Prevent actual parquet writes by patching DataFrame.to_parquet to a no-op that records calls
    parquet_calls = []

    def fake_to_parquet(self, target_path, engine=None):
        parquet_calls.append(str(target_path))

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet, raising=False)

    # Expose list to tests
    return {"tmp_path": tmp_path, "parquet_calls": parquet_calls}


def test_develop_no_based_experiments_raises_on_result_none_round_024(patch_module_defaults):
    # Setup: experiment with no based_experiments should call workspace.execute and raise when result is None
    main_exp = DummyFactorExp(based_experiments=[], workspace_path=patch_module_defaults["tmp_path"])
    # Make execute return (None, "failure") to trigger the error path at lines ~178-180
    main_exp.experiment_workspace = DummyWorkspace(patch_module_defaults["tmp_path"], execute_return=(None, "failed_run"))

    # Provide a simple runner object with a no-op deduplicate_new_factors (not used in this branch)
    class Runner:
        def deduplicate_new_factors(self, a, b):
            return b

    runner = Runner()

    with pytest.raises(fr.FactorEmptyError) as ei:
        _call_develop_impl(runner, main_exp)

    assert "failed_run" in str(ei.value)


def test_develop_with_sota_and_dedup_empty_raises_round_024(patch_module_defaults, monkeypatch):
    # Setup: two QlibFactorExperiment in based_experiments -> SOTA processing triggers
    # Create SOTA and new factor DataFrames
    sota_df = pd.DataFrame({"scol": [1, 2]})
    new_df = pd.DataFrame({"ncol": [3, 4]})

    def fake_process_factor_data(arg):
        # if given a list (sota list) return sota_df, otherwise return new_df
        if isinstance(arg, list):
            return sota_df
        return new_df

    monkeypatch.setattr(fr, "process_factor_data", fake_process_factor_data)

    # main experiment: ensure last based_experiment has a non-None result to avoid recursion
    base1 = DummyFactorExp(based_experiments=[], workspace_path=patch_module_defaults["tmp_path"], result={})
    base2 = DummyFactorExp(based_experiments=[], workspace_path=patch_module_defaults["tmp_path"], result={})
    main_exp = DummyFactorExp(based_experiments=[base1, base2], workspace_path=patch_module_defaults["tmp_path"], result={})

    # deduplicate_new_factors returns empty dataframe to trigger the FactorEmptyError at lines ~103-106
    class Runner:
        def deduplicate_new_factors(self, SOTA_factor, new_factors):
            return pd.DataFrame()

    runner = Runner()

    with pytest.raises(fr.FactorEmptyError):
        _call_develop_impl(runner, main_exp)


def test_develop_with_sota_and_timeseries_model_executes_and_sets_result_round_024(patch_module_defaults, monkeypatch):
    # Setup DataFrames
    sota_df = pd.DataFrame({"scol": [1, 2]})
    new_df = pd.DataFrame({"ncol": [3, 4]})
    dedup_df = pd.DataFrame({"ncol": [3, 4]})

    # process_factor_data returns based on input
    def fake_process_factor_data(arg):
        if isinstance(arg, list):
            return sota_df
        return new_df

    monkeypatch.setattr(fr, "process_factor_data", fake_process_factor_data)

    # Create a model experiment that will be discovered in reversed(based_experiments)
    # Provide required sub_workspace_list and sub_tasks
    sub_workspace = DummySubWorkspace({"model.py": "print('model')"})
    sub_task = DummySubTask(model_type="TimeSeries", training_hyperparameters={"n_epochs": 7, "lr": 0.01})
    model_exp = DummyModelExp(sub_workspace_list=[sub_workspace], sub_tasks=[sub_task])

    # Other base experiments that are factor experiments
    base_factor = DummyFactorExp(based_experiments=[], workspace_path=patch_module_defaults["tmp_path"], result={})

    # main experiment: based_experiments with several entries including the model exp so exist_sota_model_exp=True
    main_exp = DummyFactorExp(based_experiments=[base_factor, model_exp], workspace_path=patch_module_defaults["tmp_path"])

    # Replace experiment_workspace on main exp to capture execute env and return successful result
    exec_workspace = DummyWorkspace(patch_module_defaults["tmp_path"], execute_return=("RESULT_OK", "STDOUT_OK"))
    main_exp.experiment_workspace = exec_workspace

    # Runner with deduplicate returning non-empty DF
    class Runner:
        def deduplicate_new_factors(self, SOTA_factor, new_factors):
            # confirm SOTA and new_factors passed correctly
            assert not SOTA_factor.empty
            assert not new_factors.empty
            return dedup_df

    runner = Runner()

    # Call develop and verify result propagation and that execute saw env with TimeSeries dataset
    returned = _call_develop_impl(runner, main_exp)

    assert returned.result == "RESULT_OK"
    assert returned.stdout == "STDOUT_OK"

    # validate that execute was called and that run_env contains TimeSeries dataset keys
    assert exec_workspace.execute_called_with is not None
    run_env = exec_workspace.execute_called_with.get("run_env")
    # dataset_cls and num_features should be present for TimeSeries branch
    assert run_env is not None and run_env.get("dataset_cls") == "TSDatasetH"
    assert "num_features" in run_env
