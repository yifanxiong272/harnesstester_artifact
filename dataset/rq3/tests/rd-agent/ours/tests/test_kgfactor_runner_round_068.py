import pandas as pd
import pytest
from pathlib import Path
from types import SimpleNamespace

from rdagent.scenarios.kaggle.developer.runner import KGFactorRunner, FactorEmptyError, CoderError


class FakeWorkspace:
    def __init__(self, path: Path):
        self.workspace_path = Path(path)
        self.files = {}
        self.data_description = []
        # default execute result for the main experiment workspace
        self.execute_result = "final_result"

    def inject_files(self, **kwargs):
        # preserve payload shape: mapping of filename->content
        self.files.update(kwargs)

    def execute(self, run_env=None):
        # match signature (run_env optional) and return whatever was preconfigured
        return self.execute_result


class FakeSubWorkspace:
    def __init__(self, file_dict, exec_df, task_info=("task",)):
        # file_dict expected shape by code under test
        self.file_dict = file_dict
        # exec_df is the DataFrame-like object or None that will be used as [1] from execute()
        self._exec_df = exec_df
        self.target_task = SimpleNamespace(get_task_information=lambda: task_info)

    def execute(self):
        # code under test accesses index [1]
        return (None, self._exec_df)


def make_dummy_df(cols=5, rows=3):
    # deterministic small DataFrame with a stable shape
    data = {f"c{i}": list(range(rows)) for i in range(cols)}
    return pd.DataFrame(data)


def test_develop_happy_path_round_068(tmp_path):
    # Setup a fake workspace directory with an initial feature file count of 1
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    feature_dir = ws_dir / "feature"
    feature_dir.mkdir()
    # create one existing feature file so count = 1
    (feature_dir / "feature_00000.py").write_text("# existing feature")

    fw = FakeWorkspace(ws_dir)

    # Create a sub workspace that will be implemented
    df = make_dummy_df(cols=5, rows=10)
    sub_ws = FakeSubWorkspace(file_dict={"factor.py": "print('factor')"}, exec_df=df)

    # Experiment container mimic with the attributes used by KGFactorRunner.develop
    exp = SimpleNamespace()
    exp.experiment_workspace = fw
    exp.sub_workspace_list = [SimpleNamespace(file_dict={}), sub_ws]
    exp.based_experiments = [SimpleNamespace(result=None)]
    exp.sub_results = None
    exp.result = None

    # Create a sub_submission_score.csv to exercise the branch that reads scores
    csv_path = ws_dir / "sub_submission_score.csv"
    pd.DataFrame({"Model": ["A"], "score": [0.42]}).to_csv(csv_path, index=False)

    # Patch KGFactorRunner.init_develop to simulate initialization of based experiment
    def fake_init(self, ex):
        ex.result = "inited"
        return ex

    KGFactorRunner.init_develop = fake_init

    # Avoid calling the real __init__ which requires a 'scen' argument
    runner = object.__new__(KGFactorRunner)

    # Call the underlying wrapped function to avoid cache decorator side-effects
    res_exp = KGFactorRunner.develop.__wrapped__(runner, exp)

    # Oracles / Assertions
    assert res_exp is exp
    # result from FakeWorkspace.execute should be set
    assert exp.result == "final_result"
    # injected feature file should exist in the workspace.files mapping
    # the name uses zero-padded count starting from current_feature_file_count=1
    expected_name = "feature/feature_00001.py"
    assert expected_name in exp.experiment_workspace.files
    # data_description should have appended a tuple with task info and feature_shape (cols)
    assert len(exp.experiment_workspace.data_description) == 1
    task_info, feature_shape = exp.experiment_workspace.data_description[0]
    assert task_info == sub_ws.target_task.get_task_information()
    assert feature_shape == df.shape[-1]
    # sub_results should be populated from CSV
    assert exp.sub_results == {"A": 0.42}


def test_develop_no_factors_raises_FactorEmptyError_round_068(tmp_path):
    # workspace with no feature files
    ws_dir = tmp_path / "workspace2"
    ws_dir.mkdir()
    fw = FakeWorkspace(ws_dir)

    # All sub workspaces have empty file_dict -> should trigger FactorEmptyError
    exp = SimpleNamespace()
    exp.experiment_workspace = fw
    exp.sub_workspace_list = [FakeSubWorkspace(file_dict={}, exec_df=None), SimpleNamespace(file_dict={})]
    exp.based_experiments = []

    # create runner without invoking __init__
    runner = object.__new__(KGFactorRunner)

    with pytest.raises(FactorEmptyError):
        KGFactorRunner.develop.__wrapped__(runner, exp)


def test_develop_no_result_raises_CoderError_round_068(tmp_path):
    # workspace where main execute returns None -> should raise CoderError
    ws_dir = tmp_path / "workspace3"
    ws_dir.mkdir()
    fw = FakeWorkspace(ws_dir)
    fw.execute_result = None  # cause the execute(run_env=..) to return None

    # create one valid sub workspace so implemented_factor_count > 0
    df = make_dummy_df(cols=2, rows=2)
    sub_ws = FakeSubWorkspace(file_dict={"factor.py": "x"}, exec_df=df)

    exp = SimpleNamespace()
    exp.experiment_workspace = fw
    exp.sub_workspace_list = [sub_ws]
    exp.based_experiments = []

    runner = object.__new__(KGFactorRunner)

    with pytest.raises(CoderError):
        KGFactorRunner.develop.__wrapped__(runner, exp)
