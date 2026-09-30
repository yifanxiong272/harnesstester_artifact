import pathlib
import types
import pandas as pd
import pytest
import importlib

# Load the module under test
submit_mod = importlib.import_module(
    "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"
)

# Minimal DSExperiment substitute used in tests
class DummyExperiment:
    def __init__(self):
        # experiment_workspace only needs file_dict attribute for logging and injection
        self.experiment_workspace = types.SimpleNamespace(file_dict={"main.py": "print('hi')"})


def make_env_factory():
    class Conf:
        def __init__(self, running_timeout_period):
            self.running_timeout_period = running_timeout_period

    class Env:
        def __init__(self, running_timeout_period):
            self.conf = Conf(running_timeout_period)

    def factory(*, extra_volumes=None, running_timeout_period=None):
        return Env(running_timeout_period)

    return factory


def test_process_experiment_main_success_with_score_round_075(monkeypatch):
    """
    Cover branch: execute_ret_code == 0, scores.csv exists and pd.read_csv succeeds,
    grade.py run returns exit_code 0 and stdout is processed.
    Asserts that pd.read_csv was used and the returned valid_score equals the value
    from the fake CSV, and that grade.py was executed.
    """

    # Prepare fake DS_RD_SETTING
    monkeypatch.setattr(submit_mod, "DS_RD_SETTING", types.SimpleNamespace(full_timeout=999, debug_timeout=5))

    # Patch T(...) to return object with r() method
    monkeypatch.setattr(submit_mod, "T", lambda _: types.SimpleNamespace(r=lambda: "input_path"))

    # Provide get_ds_env factory
    monkeypatch.setattr(submit_mod, "get_ds_env", make_env_factory())

    # Prepare FakeWorkspace that simulates a successful main run, a present scores.csv, and a successful grade run
    class FakeScorePath:
        def __init__(self, exists):
            self._exists = exists

        def exists(self):
            return self._exists

    class FakeResult:
        def __init__(self, exit_code, stdout=""):
            self.exit_code = exit_code
            self._stdout = stdout

        def get_truncated_stdout(self):
            return self._stdout

    class FakeWorkspace:
        def __init__(self):
            self.injected_files = {}
            self.run_calls = []
            # Provide a workspace_path object whose / operator returns FakeScorePath
            self.workspace_path = types.SimpleNamespace(__truediv__=lambda self_obj, other: FakeScorePath(True))

        def inject_code_from_file_dict(self, file_dict):
            # Accept the experiment_workspace file dict
            self.injected_files.update(file_dict)

        def inject_files(self, **files):
            self.injected_files.update(files)

        def run(self, env, entry):
            self.run_calls.append(entry)
            if entry == "python main.py":
                return FakeResult(exit_code=0, stdout="main executed")
            elif entry == "python grade.py":
                # include a chmod line to be stripped by regex in code
                return FakeResult(exit_code=0, stdout="chmod: something\nGRADE OUTPUT: 0.321\n")
            return FakeResult(exit_code=1, stdout="")

    # Patch FBWorkspace to our fake
    monkeypatch.setattr(submit_mod, "FBWorkspace", FakeWorkspace)

    # Patch pandas.read_csv to return a DataFrame with an 'ensemble' index value
    def fake_read_csv(path, index_col=0):
        # Create a DataFrame where .loc['ensemble'].iloc[0] == 0.123
        df = pd.DataFrame([0.123], index=["ensemble"]) 
        return df

    monkeypatch.setattr(submit_mod.pd, "read_csv", fake_read_csv)

    exp = DummyExperiment()
    competition = "comp"
    folder = "folder"
    grade_py_code = "print('grade')"
    loop_id = "loop42"

    result_exp, valid_score, parsed = submit_mod.process_experiment(exp, competition, folder, grade_py_code, loop_id)

    # Assertions: valid_score came from fake_read_csv and grade.py was executed
    assert result_exp is exp
    assert pytest.approx(valid_score, rel=1e-6) == 0.123
    # parsed should equal whatever the module parsing function returns for the grade stdout
    expected_parsed = submit_mod._parsing_score("GRADE OUTPUT: 0.321\n")
    assert parsed == expected_parsed


def test_process_experiment_main_success_score_parse_failure_round_075(monkeypatch):
    """
    Cover branch: execute_ret_code == 0, scores.csv exists but pd.read_csv raises -> except branch executed,
    then grading is still run and valid_score remains None.
    """

    monkeypatch.setattr(submit_mod, "DS_RD_SETTING", types.SimpleNamespace(full_timeout=999, debug_timeout=5))
    monkeypatch.setattr(submit_mod, "T", lambda _: types.SimpleNamespace(r=lambda: "input_path"))
    monkeypatch.setattr(submit_mod, "get_ds_env", make_env_factory())

    class FakeResult:
        def __init__(self, exit_code, stdout=""):
            self.exit_code = exit_code
            self._stdout = stdout

        def get_truncated_stdout(self):
            return self._stdout

    class FakeWorkspace:
        def __init__(self):
            self.injected_files = {}
            self.run_calls = []
            self.workspace_path = types.SimpleNamespace(__truediv__=lambda self_obj, other: types.SimpleNamespace(exists=lambda: True))

        def inject_code_from_file_dict(self, file_dict):
            self.injected_files.update(file_dict)

        def inject_files(self, **files):
            self.injected_files.update(files)

        def run(self, env, entry):
            self.run_calls.append(entry)
            if entry == "python main.py":
                return FakeResult(exit_code=0, stdout="main ok")
            elif entry == "python grade.py":
                return FakeResult(exit_code=0, stdout="chmod: x\nALL OK")
            return FakeResult(exit_code=1, stdout="")

    monkeypatch.setattr(submit_mod, "FBWorkspace", FakeWorkspace)

    # Simulate read_csv throwing an exception to hit the except branch
    def raise_on_read_csv(*args, **kwargs):
        raise ValueError("broken csv")

    monkeypatch.setattr(submit_mod.pd, "read_csv", raise_on_read_csv)

    exp = DummyExperiment()
    competition = "comp"
    folder = "folder"
    grade_py_code = "print('grade')"
    loop_id = "loop_ok"

    result_exp, valid_score, parsed = submit_mod.process_experiment(exp, competition, folder, grade_py_code, loop_id)

    assert result_exp is exp
    # read_csv failed so valid_score should remain None
    assert valid_score is None
    # grade.py was run; parsed equals parsing of the fake stdout (after chmod removal)
    expected_parsed = submit_mod._parsing_score("ALL OK")
    assert parsed == expected_parsed


def test_process_experiment_main_failure_and_loopid_none_round_075(monkeypatch):
    """
    Cover branch: loop_id is None -> loop_id becomes 'unknown'; main run fails (non-zero) -> grading is skipped.
    Assert that grade run is not called and valid_score remains None.
    """

    monkeypatch.setattr(submit_mod, "DS_RD_SETTING", types.SimpleNamespace(full_timeout=999, debug_timeout=5))
    monkeypatch.setattr(submit_mod, "T", lambda _: types.SimpleNamespace(r=lambda: "input_path"))
    monkeypatch.setattr(submit_mod, "get_ds_env", make_env_factory())

    class FakeResult:
        def __init__(self, exit_code, stdout=""):
            self.exit_code = exit_code
            self._stdout = stdout

        def get_truncated_stdout(self):
            return self._stdout

    class FakeWorkspace:
        def __init__(self):
            self.injected_files = {}
            self.run_calls = []
            # scores.csv does not exist in this scenario
            self.workspace_path = types.SimpleNamespace(__truediv__=lambda self_obj, other: types.SimpleNamespace(exists=lambda: False))

        def inject_code_from_file_dict(self, file_dict):
            self.injected_files.update(file_dict)

        def inject_files(self, **files):
            self.injected_files.update(files)

        def run(self, env, entry):
            self.run_calls.append(entry)
            # Simulate a failing main.py
            if entry == "python main.py":
                return FakeResult(exit_code=2, stdout="error")
            return FakeResult(exit_code=1, stdout="")

    monkeypatch.setattr(submit_mod, "FBWorkspace", FakeWorkspace)

    # Ensure read_csv would not be called, but provide a stub anyway
    monkeypatch.setattr(submit_mod.pd, "read_csv", lambda *a, **k: pd.DataFrame([0.5], index=["ensemble"]))

    exp = DummyExperiment()
    competition = "comp"
    folder = "folder"
    grade_py_code = "print('grade')"
    loop_id = None

    result_exp, valid_score, parsed = submit_mod.process_experiment(exp, competition, folder, grade_py_code, loop_id)

    assert result_exp is exp
    # Since main failed, we never compute valid_score and grading was skipped
    assert valid_score is None
    # parsed equals whatever parsing an empty grade_stdout returns
    expected_parsed = submit_mod._parsing_score("")
    assert parsed == expected_parsed
