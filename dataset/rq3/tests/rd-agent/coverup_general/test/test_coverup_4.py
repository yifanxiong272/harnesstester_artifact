# file: rdagent/scenarios/data_science/dev/runner/eval.py:74-276
# asked: {"lines": [82, 83, 84, 85, 86, 88, 91, 92, 96, 97, 98, 99, 102, 103, 104, 105, 107, 108, 109, 110, 111, 112, 113, 114, 117, 118, 121, 122, 123, 124, 125, 126, 127, 129, 130, 131, 132, 133, 138, 139, 140, 141, 142, 143, 144, 145, 146, 148, 149, 150, 153, 154, 155, 157, 158, 159, 160, 163, 164, 165, 167, 168, 169, 173, 174, 176, 179, 180, 184, 185, 186, 187, 189, 192, 193, 194, 196, 199, 201, 202, 203, 204, 206, 207, 208, 209, 210, 211, 212, 213, 216, 218, 219, 222, 223, 224, 225, 226, 227, 228, 231, 233, 234, 235, 236, 237, 238, 240, 241, 242, 243, 244, 246, 247, 248, 249, 251, 252, 254, 255, 256, 257, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 270, 271, 272, 273, 274, 275, 276], "branches": [[109, 110], [109, 111], [124, 125], [124, 129], [138, 139], [138, 148], [139, 140], [139, 142], [142, 143], [142, 145], [145, 146], [145, 153], [148, 149], [148, 153], [153, 154], [153, 163], [167, 168], [167, 173], [173, 174], [173, 176], [186, 187], [186, 189], [192, 193], [192, 196], [231, 233], [231, 270], [235, 236], [235, 270], [241, 242], [241, 246], [242, 241], [242, 243], [246, 247], [246, 251], [259, 260], [259, 270], [262, 263], [262, 266], [266, 267], [266, 270], [270, 271], [270, 273], [273, 274], [273, 276]]}
# gained: {"lines": [82, 83, 84, 85, 86, 88, 91, 92, 96, 97, 98, 99, 102, 103, 104, 105, 107, 108, 109, 111, 112, 113, 114, 117, 118, 121, 122, 123, 124, 125, 126, 127, 129, 130, 131, 132, 133, 138, 148, 153, 163, 164, 165, 167, 168, 169, 173, 174, 176, 179, 180, 184, 185, 186, 189, 192, 193, 194, 199, 201, 202, 203, 204, 206, 207, 208, 209, 210, 211, 212, 213, 216, 218, 219, 222, 223, 227, 228, 231, 233, 234, 235, 236, 237, 238, 240, 241, 242, 246, 247, 248, 249, 251, 252, 254, 255, 256, 257, 259, 260, 261, 262, 263, 264, 265, 270, 271, 272, 273, 274, 275, 276], "branches": [[109, 111], [124, 125], [124, 129], [138, 148], [148, 153], [153, 163], [167, 168], [167, 173], [173, 174], [173, 176], [186, 189], [192, 193], [231, 233], [231, 270], [235, 236], [241, 242], [241, 246], [242, 241], [246, 247], [259, 260], [262, 263], [270, 271], [270, 273], [273, 274], [273, 276]]}

import json
import re
from datetime import timedelta
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest

import rdagent.scenarios.data_science.dev.runner.eval as eval_mod


class FakeResult:
    def __init__(self, stdout, exit_code=0, running_time=1.0):
        self._stdout = stdout
        self.stdout = stdout
        self.exit_code = exit_code
        self.running_time = running_time

    def get_truncated_stdout(self):
        return self._stdout


class FakeRunningInfo:
    def __init__(self, running_time=1.0):
        self.running_time = running_time


class FakeImplementation:
    DEL_KEY = "<DEL>"

    def __init__(self, workspace_path: Path, file_dict=None, all_codes="", change_summary=""):
        self.workspace_path = workspace_path
        self.file_dict = file_dict or {}
        self.all_codes = all_codes
        self.change_summary = change_summary
        self.running_info = FakeRunningInfo()
        self._injected = {}
        self._executed_entries = []

    def execute(self, env=None, entry=None):
        # Record calls and simulate clear workspace or coverage json command.
        self._executed_entries.append(entry)
        if entry == "clear":
            return SimpleNamespace(stdout="", exit_code=0)
        if entry == "python -m coverage json -o coverage.json":
            # create a coverage.json if it does not exist; content depends on workspace content
            cov_path = self.workspace_path / "coverage.json"
            # Default used files: if any file 'used_files.json' exists, use it for determinism
            used_file = self.workspace_path / "used_files.json"
            if used_file.exists():
                used = json.loads(used_file.read_text())
            else:
                used = {"files": {}}
            cov_path.write_text(json.dumps(used))
            return SimpleNamespace(stdout="", exit_code=0)
        return SimpleNamespace(stdout="", exit_code=0)

    def run(self, env=None, entry=None):
        # Simulate producing stdout with EDA markers and typical content.
        stdout = "start\n=== Start of EDA part ===\nEDA_CONTENT\n=== End of EDA part ===\nend"
        # Create a result that also sets running time
        res = FakeResult(stdout=stdout, exit_code=0, running_time=2.0)
        return res

    def inject_files(self, **kwargs):
        # store injected values; if DEL_KEY provided, remove the file physically
        for k, v in kwargs.items():
            if v == self.DEL_KEY:
                fp = Path(self.workspace_path) / k
                if fp.exists():
                    fp.unlink()
                self._injected[k] = self.DEL_KEY
                # also remove from file_dict if present
                self.file_dict.pop(k, None)
            else:
                dest = Path(self.workspace_path) / k
                dest.write_text(v)
                self._injected[k] = v

    @property
    def injected(self):
        return self._injected


class FakeEnv:
    def __init__(self, running_timeout_period):
        self.conf = SimpleNamespace(running_timeout_period=running_timeout_period)


class FakeTimer:
    def __init__(self, remain_td=None, all_duration=None):
        self._remain = remain_td
        self.all_duration = all_duration

    def remain_time(self):
        return self._remain


class DummyFeedback:
    def __init__(self):
        self.acceptable = True
        self.hyperparameter_tuning_decision = False
        self.score = None
        self.final_decision = True
        self.code = ""
        self.return_checking = ""


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch):
    # Patch functions and settings used in evaluator module
    monkeypatch.setattr(eval_mod, "get_clear_ws_cmd", lambda: "clear")
    # Default DS_RD_SETTING object replacement with attributes used
    class _DS:
        local_data_path = "/tmp"
        coder_on_whole_pipeline = True
        dump_stdout_type = "short"
        only_first_loop_enable_hyperparameter_tuning = True
        time_ratio_limit_to_enable_hyperparameter_tuning = 0.99
        only_enable_tuning_in_merge = False
        merge_hours = 1
        res_time_ratio_limit_to_enable_hyperparameter_tuning = 0.99

    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", _DS())
    # Patch get_ds_env to return FakeEnv
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda extra_volumes=None, running_timeout_period=None: FakeEnv(running_timeout_period or 100.0))
    # remove_eda_part - remove the EDA part markers and content
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: re.sub(r"=== Start of EDA part ===.*?=== End of EDA part ===", "", s, flags=re.DOTALL))
    # Patch timer wrapper
    eval_mod.RD_Agent_TIMER_wrapper.timer = FakeTimer(remain_td=timedelta(hours=10), all_duration=timedelta(hours=20))
    # Patch get_test_eval default
    class FakeTestEval:
        def enabled(self, competition):
            return False

        def valid(self, competition, implementation):
            return "", 0

    monkeypatch.setattr(eval_mod, "get_test_eval", lambda: FakeTestEval())
    # Patch build_cls_from_json_with_retry to return a DummyFeedback
    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", lambda cls, system_prompt=None, user_prompt=None: DummyFeedback())
    # Patch DSRunnerCoSTEERSettings to provide dump_stdout_type
    monkeypatch.setattr(eval_mod, "DSRunnerCoSTEERSettings", lambda: SimpleNamespace(dump_stdout_type="short"))
    yield


def make_queried_knowledge(task_info):
    qk = SimpleNamespace()
    qk.task_to_former_failed_traces = {task_info: [[]]}
    return qk


def make_target_task(task_info):
    t = SimpleNamespace()
    t.get_task_information = lambda: task_info
    return t


def make_scen(metric_name="accuracy", competition="comp"):
    scen = SimpleNamespace()
    scen.competition = competition
    scen.real_full_timeout = lambda: 100.0
    scen.get_scenario_all_desc = lambda eda_output=None: f"SCENARIO_DESC (EDA:{eda_output})"
    scen.metric_name = metric_name
    return scen


def test_evaluate_missing_scores_and_submission_fail(tmp_path, monkeypatch):
    # Setup evaluator with scen argument as required by CoSTEEREvaluator.__init__
    scen = make_scen(metric_name="accuracy", competition="comp1")
    evaluator = eval_mod.DSRunnerEvaluator(scen)

    # Implementation without scores.csv
    impl = FakeImplementation(workspace_path=tmp_path, file_dict={"model_a.py": "print('model')"})
    # Ensure no scores.csv present
    scores_fp = tmp_path / "scores.csv"
    if scores_fp.exists():
        scores_fp.unlink()

    # Patch get_test_eval to simulate enabled and invalid submission
    class FakeTE:
        def enabled(self, competition):
            return True

        def valid(self, competition, implementation):
            return ("Submission is invalid", 1)

    monkeypatch.setattr(eval_mod, "get_test_eval", lambda: FakeTE())

    # Make queried knowledge and task
    task = make_target_task("task_missing_scores")
    qk = make_queried_knowledge("task_missing_scores")

    # Patch DS_RD_SETTING to have coder_on_whole_pipeline True to skip coverage branch
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", SimpleNamespace(
        local_data_path="/tmp",
        coder_on_whole_pipeline=True,
        dump_stdout_type="short",
        only_first_loop_enable_hyperparameter_tuning=True,
        time_ratio_limit_to_enable_hyperparameter_tuning=0.99,
        only_enable_tuning_in_merge=False,
        merge_hours=1,
        res_time_ratio_limit_to_enable_hyperparameter_tuning=0.99
    ))

    # Ensure DSRunnerCoSTEERSettings returns default dump_stdout_type
    monkeypatch.setattr(eval_mod, "DSRunnerCoSTEERSettings", lambda: SimpleNamespace(dump_stdout_type="short"))

    # Run evaluate
    feedback = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=qk)

    # Assertions: missing scores should cause unacceptable and error text
    assert feedback is not None
    assert feedback.acceptable is False
    assert "Metrics file" in feedback.return_checking or "Metrics file" in feedback.return_checking
    # Submission check failed should be appended or indicated
    assert "Submission file check failed" in feedback.return_checking or "Submission is invalid" in feedback.return_checking


def test_evaluate_with_scores_and_coverage_unused_files(tmp_path, monkeypatch):
    # Setup evaluator with scen
    scen = make_scen(metric_name="Accuracy", competition="comp2")
    evaluator = eval_mod.DSRunnerEvaluator(scen)

    # Create workspace and files
    workspace = tmp_path
    (workspace / "model_a.py").write_text("print('model a')")
    (workspace / "main.py").write_text("print('main')")
    (workspace / "load_data.py").write_text("print('load')")
    (workspace / "feature.py").write_text("print('feature')")
    (workspace / "ensemble.py").write_text("print('ensemble')")
    (workspace / "unused.py").write_text("print('unused')")

    # Prepare implementation with file_dict entries
    file_dict = {"model_a.py": "print('m')", "load_data.py": "x", "feature.py": "y", "ensemble.py": "z", "main.py": "m"}
    impl = FakeImplementation(workspace_path=workspace, file_dict=file_dict)

    # Create scores.csv such that model_set_in_scores matches model_set_in_folder.union({'ensemble'})
    df = pd.DataFrame({"Accuracy": [0.5, 0.6]}, index=["ensemble", "model_a"])
    (workspace / "scores.csv").write_text(df.to_csv())

    # Patch get_test_eval to be disabled
    monkeypatch.setattr(eval_mod, "get_test_eval", lambda: SimpleNamespace(enabled=lambda comp: False, valid=lambda comp, impl: ("", 0)))

    # Ensure DS_RD_SETTING configured to allow coverage branch
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", SimpleNamespace(
        local_data_path="/tmp",
        coder_on_whole_pipeline=False,
        dump_stdout_type="full",
        only_first_loop_enable_hyperparameter_tuning=False,
        time_ratio_limit_to_enable_hyperparameter_tuning=0.99,
        only_enable_tuning_in_merge=False,
        merge_hours=1,
        res_time_ratio_limit_to_enable_hyperparameter_tuning=0.99
    ))

    # Ensure DSRunnerCoSTEERSettings returns dump_stdout_type 'full' to exercise that branch
    monkeypatch.setattr(eval_mod, "DSRunnerCoSTEERSettings", lambda: SimpleNamespace(dump_stdout_type="full"))

    # Create a used_files.json that contains files not including any model_ file to trigger "No model script is used"
    used = {"files": {"main.py": {}, "some_other.py": {}}}
    (workspace / "used_files.json").write_text(json.dumps(used))

    # Make task and queried knowledge
    task = make_target_task("task_with_scores")
    qk = make_queried_knowledge("task_with_scores")

    # Run evaluator
    feedback = evaluator.evaluate(target_task=task, implementation=impl, gt_implementation=None, queried_knowledge=qk)

    # Assertions: since coverage report indicates no model used, feedback should be unacceptable
    assert feedback is not None
    assert feedback.acceptable is False
    # Code should include error message about no model script used or about must-have files
    assert "[Error]" in feedback.code or "No model script" in feedback.code or "must be used" in feedback.code
    # Score attribute should exist
    assert hasattr(feedback, "score")
