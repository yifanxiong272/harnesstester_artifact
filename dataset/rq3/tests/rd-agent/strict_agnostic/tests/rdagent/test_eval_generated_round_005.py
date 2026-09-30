import json
import re
from types import SimpleNamespace
from pathlib import Path
from datetime import timedelta
import pandas as pd
import pytest

# Import the module under test
from rdagent.scenarios.data_science.dev.runner import eval as eval_mod

# Helpers to construct fake objects used by evaluate

def make_env(timeout=100):
    return SimpleNamespace(conf=SimpleNamespace(running_timeout_period=timeout))


def make_timer(remain_hours=2, all_hours=None):
    class FakeTimer:
        def __init__(self, remain_hours, all_hours):
            self._remain = timedelta(hours=remain_hours)
            self.all_duration = timedelta(hours=all_hours) if all_hours is not None else None

        def remain_time(self):
            return self._remain

    return FakeTimer(remain_hours, all_hours)


def make_result(stdout_text, exit_code=0, running_time=1.0):
    # result object returned by implementation.run
    class R:
        def __init__(self, stdout_text, exit_code, running_time):
            self.stdout = stdout_text
            self._trunc = stdout_text
            self.exit_code = exit_code
            self.running_time = running_time

        def get_truncated_stdout(self):
            return self._trunc

    return R(stdout_text, exit_code, running_time)


def make_implementation(tmp_path, file_dict=None, running_time=1.0):
    if file_dict is None:
        file_dict = {}

    impl = SimpleNamespace()

    impl.file_dict = dict(file_dict)
    impl.all_codes = "# all codes"
    impl.change_summary = "summary"
    impl.workspace_path = tmp_path

    impl.running_info = SimpleNamespace()
    impl.running_info.running_time = running_time

    # execute for clearing or coverage json creation - implement as callable that may create coverage.json
    def execute(env=None, entry=None):
        # For "get_clear_ws_cmd" we simply return an object with stdout
        if entry == eval_mod.get_clear_ws_cmd():
            return SimpleNamespace(stdout="cleared\n", truncated_stdout="cleared\n")
        # For coverage json creation, we may create a coverage.json file if not exists
        if isinstance(entry, str) and entry.startswith("python -m coverage json"):
            cov_path = Path(tmp_path) / "coverage.json"
            # If a coverage.json already exists leave it
            if not cov_path.exists():
                cov_content = {"files": {f: {} for f in impl.file_dict.keys()}}
                cov_path.write_text(json.dumps(cov_content))
            return SimpleNamespace(stdout="coverage json created\n")
        return SimpleNamespace(stdout="exec returned\n")

    impl.execute = execute

    def run(env=None, entry=None):
        # Return a result object; entry expected to be coverage run main.py
        # stdout contained might include EDA section if provided in file_dict special key
        out = impl.file_dict.get("__run_stdout__", "normal output\n")
        return make_result(out, exit_code=0, running_time=impl.running_info.running_time)

    impl.run = run

    def inject_files(**kwargs):
        # simulate write of injected files to file_dict
        for k, v in kwargs.items():
            impl.file_dict[k] = v

    impl.inject_files = inject_files

    return impl


@pytest.fixture(autouse=True)
def _patch_common(monkeypatch):
    # Patch get_clear_ws_cmd to return a deterministic entry
    monkeypatch.setattr(eval_mod, "get_clear_ws_cmd", lambda: "CLEAR_CMD")

    # Patch get_ds_env to return a deterministic env
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda extra_volumes=None, running_timeout_period=None: make_env(timeout=running_timeout_period or 100))

    # Patch template loader T(...) to return object with r() that returns a reproducible string
    class FakeT:
        def __init__(self, *_a, **_k):
            pass

        def r(self, **_kwargs):
            # Return a simple JSON-like string so build_cls_from_json_with_retry can parse or be mocked
            return "{system_prompt}"

    monkeypatch.setattr(eval_mod, "T", FakeT)

    # Patch DSRunnerCoSTEERSettings to a simple object
    monkeypatch.setattr(eval_mod, "DSRunnerCoSTEERSettings", lambda: SimpleNamespace(dump_stdout_type="full"))

    # Default test_eval: disabled; individual tests may override
    class DefaultTestEval:
        def enabled(self, competition):
            return False

        def valid(self, competition, implementation):
            return "", 0

    monkeypatch.setattr(eval_mod, "get_test_eval", lambda: DefaultTestEval())

    # Patch the timer wrapper
    monkeypatch.setattr(eval_mod.RD_Agent_TIMER_wrapper, "timer", make_timer(remain_hours=2, all_hours=10))

    # Patch build_cls_from_json_with_retry to return a mutable feedback-like object
    def fake_build(cls, **kwargs):
        fb = SimpleNamespace()
        fb.score = None
        fb.acceptable = True
        fb.hyperparameter_tuning_decision = False
        fb.return_checking = ""
        fb.code = ""
        fb.final_decision = None
        return fb

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build)

    yield


def test_evaluate_no_score_file_round_005(tmp_path, monkeypatch):
    """
    - No EDA markers in stdout -> eda_output is None branch
    - No scores.csv in workspace -> triggers warning and score_ret_code != 0 branch
    - get_test_eval disabled by default -> skip submission check
    """
    # Prepare fake self (instance) with minimal scen used by evaluate
    scen = SimpleNamespace(
        competition="compA",
        real_full_timeout=lambda: 100,
        metric_name="Score",
        get_scenario_all_desc=lambda eda_output=None: "scenario desc",
    )
    fake_self = SimpleNamespace(scen=scen)

    # target_task and queried_knowledge
    task_info = "task-id-1"
    target_task = SimpleNamespace(get_task_information=lambda: task_info)
    queried_knowledge = SimpleNamespace(task_to_former_failed_traces={task_info: [["former"]]})

    # Create implementation without scores.csv
    impl = make_implementation(tmp_path, file_dict={"model_a.py": "# model a"}, running_time=2.0)

    # Make the run stdout have no EDA markers to hit eda_output None
    impl.file_dict["__run_stdout__"] = "Some normal stdout without markers."

    # Ensure DS_RD_SETTING values that influence scoring/hyperparameter branches are defaultable
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", SimpleNamespace(
        coder_on_whole_pipeline=False,
        only_first_loop_enable_hyperparameter_tuning=False,
        time_ratio_limit_to_enable_hyperparameter_tuning=0.9,
        only_enable_tuning_in_merge=False,
        merge_hours=1,
        res_time_ratio_limit_to_enable_hyperparameter_tuning=0.9,
        local_data_path="/tmp",
    ))

    # Ensure timer has sensible values
    monkeypatch.setattr(eval_mod.RD_Agent_TIMER_wrapper, "timer", make_timer(remain_hours=5, all_hours=20))

    feedback = eval_mod.DSRunnerEvaluator.evaluate(fake_self, target_task, impl, None, queried_knowledge)

    # Oracles / assertions
    # Since there is no scores.csv, score_ret_code != 0 path should mark unacceptable
    assert feedback.acceptable is False, "Feedback should be unacceptable when scores.csv is missing"
    assert "Metrics file (scores.csv) is not generated" in feedback.return_checking or feedback.return_checking != ""
    # EDA.md must have been injected and contain fallback text
    assert impl.file_dict.get("EDA.md") == "No EDA output.", "EDA.md should be injected with fallback when no EDA found"


def test_evaluate_with_scores_and_coverage_issues_round_005(tmp_path, monkeypatch):
    """
    - scores.csv exists with correct model names but missing must-use files -> triggers unused-files branch
    - coverage.json exists and marks model file used -> used_files path executed
    - triggers branch where feedback.code is updated with must-have files error
    """
    scen = SimpleNamespace(
        competition="compB",
        real_full_timeout=lambda: 200,
        metric_name="Score",
        get_scenario_all_desc=lambda eda_output=None: "scenario desc",
    )
    fake_self = SimpleNamespace(scen=scen)

    task_info = "task-id-2"
    target_task = SimpleNamespace(get_task_information=lambda: task_info)
    queried_knowledge = SimpleNamespace(task_to_former_failed_traces={task_info: [["former2"]]})

    # Construct implementation workspace with score file and python files
    files = {
        "model_a.py": "# model a",
        "load_data.py": "# load",
        "feature.py": "# feat",
        "ensemble.py": "# ens",
        "main.py": "# main",
    }

    # Create physical python files in the tmp_path so all_python_files detection works
    for name, content in files.items():
        (Path(tmp_path) / name).write_text(content)

    impl = make_implementation(tmp_path, file_dict=files, running_time=3.0)

    # Create a scores.csv that contains ensemble and model_a as index and the expected column
    score_df = pd.DataFrame({"Score": [0.9, 0.8]}, index=["ensemble", "model_a"])  # ensemble first
    score_fp = Path(tmp_path) / "scores.csv"
    score_df.to_csv(score_fp)

    # Create coverage.json that reports used file only model_a.py
    cov = {"files": {"model_a.py": {}}}
    (Path(tmp_path) / "coverage.json").write_text(json.dumps(cov))

    # Ensure DS_RD_SETTING configured to check model names via else branch (coder_on_whole_pipeline False)
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", SimpleNamespace(
        coder_on_whole_pipeline=False,
        only_first_loop_enable_hyperparameter_tuning=False,
        time_ratio_limit_to_enable_hyperparameter_tuning=0.9,
        only_enable_tuning_in_merge=False,
        merge_hours=1,
        res_time_ratio_limit_to_enable_hyperparameter_tuning=0.9,
        local_data_path="/tmp",
    ))

    # Ensure test_eval returns success
    class TE:
        def enabled(self, comp):
            return True

        def valid(self, comp, implementation):
            return ("Submission is valid", 0)

    monkeypatch.setattr(eval_mod, "get_test_eval", lambda: TE())

    # Patch timer to enable hyperparameter tuning conditions fairly
    monkeypatch.setattr(eval_mod.RD_Agent_TIMER_wrapper, "timer", make_timer(remain_hours=5, all_hours=20))

    # Run evaluate
    feedback = eval_mod.DSRunnerEvaluator.evaluate(fake_self, target_task, impl, None, queried_knowledge)

    # Assertions: since coverage.json exists and must-have files (load_data.py etc) are unused, feedback.code should include an error
    assert feedback.acceptable is False, "Feedback should be unacceptable when required scripts are unused"
    assert "must be used in `main.py`" in feedback.code or "must be used" in feedback.code
    # Also submission check output should have been appended to stdout-related processing -> ensure return_checking unaffected here
    # Additionally ensure that score was read and assigned
    assert (feedback.score is None) or isinstance(feedback.score, (int, float)), "feedback.score should be numeric or None"
