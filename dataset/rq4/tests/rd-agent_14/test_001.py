import io
from types import SimpleNamespace
from pathlib import Path

import rdagent.components.coder.data_science.workflow.eval as eval_mod


def test_probe_001(tmp_path, monkeypatch):
    """
    Probe for greedy overmatch across multiple single-line EDA blocks.

    Constructs a minimal FBWorkspace mock and environment such that
    evaluate() runs the branch where scores.csv exists (score_ret_code == 0).
    Monkeypatch build_cls_from_json_with_retry to capture the user_prompt
    passed in so the test can assert that the token 'middle' (between two
    separate EDA blocks) is preserved.
    """

    # Prepare a tmp workspace and required files
    ws_path = tmp_path

    # Ensure DIRNAME/eval_tests/submission_format_test.txt exists (used by evaluate)
    eval_tests_dir = ws_path / "eval_tests"
    eval_tests_dir.mkdir()
    (eval_tests_dir / "submission_format_test.txt").write_text("print('submission ok')")

    # Prepare implementation.file_dict with main.py, spec/workflow.md and a model file
    file_dict = {
        "main.py": "print('hello')",
        "spec/workflow.md": "# spec",
        "model_a.py": "# model content",
    }

    # Create a valid scores.csv so the score checks pass
    metric_name = "acc"
    scores_csv = ws_path / "scores.csv"
    # CSV with index column (blank header) and one column named metric_name
    scores_csv.write_text(
        ",%s\nmodel_a,0.5\nensemble,0.6\n" % metric_name
    )

    # Build a deterministic single-line stdout containing two EDA blocks separated by ' middle '
    stdout_line = (
        "prefix === Start of EDA part ===EDA1=== End of EDA part ==="
        " middle === Start of EDA part ===EDA2=== End of EDA part === suffix"
    )

    class MockFBWorkspace:
        def __init__(self, workspace_path, file_dict):
            self.workspace_path = workspace_path
            self.file_dict = dict(file_dict)

        def execute(self, env, entry):
            # Called first as rm submission.csv scores.csv -> ignore
            if entry.startswith("rm "):
                return ""
            # Called for running the main program
            if "coverage run main.py" in entry:
                return stdout_line
            # Other calls: return empty
            return ""

        def execute_ret_code(self, env, entry):
            # Called for submission format test: return (out, 0)
            return ("submission ok", 0)

        def inject_files(self, **files):
            # update file_dict with injected test files
            self.file_dict.update(files)

    implementation = MockFBWorkspace(ws_path, file_dict)

    # Minimal target_task mock
    class MockTask:
        def get_task_information(self):
            return "task_info"

    target_task = MockTask()

    # Monkeypatch get_ds_env to provide a conf object with extra_volumes attr
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda: SimpleNamespace(conf=SimpleNamespace()))

    # Monkeypatch DS_RD_SETTING to provide local_data_path and spec_enabled
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", SimpleNamespace(local_data_path="/tmp", spec_enabled=True))

    # Monkeypatch DIRNAME so that evaluate can read submission_format_test.txt from our tmp path
    monkeypatch.setattr(eval_mod, "DIRNAME", ws_path)

    # Capture the user_prompt passed into build_cls_from_json_with_retry
    captured = {}

    def fake_build_cls_from_json_with_retry(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        # Create a simple feedback-like object with expected attributes
        fb = SimpleNamespace()
        fb.final_decision = True
        fb.return_checking = ""
        # Attach captured user prompt for inspection by the test
        fb.captured_user_prompt = user_prompt
        captured['user_prompt'] = user_prompt
        return fb

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build_cls_from_json_with_retry)

    # Create an evaluator instance without running __init__ (unknown signature)
    EvalClass = eval_mod.WorkflowGeneralCaseSpecEvaluator
    evaluator = EvalClass.__new__(EvalClass)

    # Provide a minimal scen object required by evaluate(): competition, metric_name, get_scenario_all_desc
    evaluator.scen = SimpleNamespace(
        competition="comp",
        metric_name=metric_name,
        get_scenario_all_desc=lambda: "scenario desc",
    )

    # Invoke the target entrypoint
    wfb = evaluator.evaluate(target_task, implementation, None, queried_knowledge=None)

    # Primary oracle: the user_prompt captured by our fake builder must contain the token 'middle'
    assert hasattr(wfb, "captured_user_prompt"), "Feedback object must expose captured_user_prompt"
    assert "middle" in wfb.captured_user_prompt, (
        "Expected the intervening text 'middle' to be preserved in user_prompt, "
        "but it was removed (indicating an over-greedy EDA removal)."
    )
