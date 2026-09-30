# file: rdagent/components/coder/data_science/pipeline/eval.py:125-348
# asked: {"lines": [134, 136, 137, 139, 140, 141, 142, 143, 144, 145, 146, 147, 150, 151, 152, 155, 156, 157, 159, 160, 163, 164, 166, 168, 169, 170, 171, 172, 173, 174, 175, 176, 178, 179, 180, 181, 182, 186, 187, 188, 190, 191, 192, 193, 194, 196, 197, 198, 200, 201, 202, 204, 205, 206, 207, 208, 209, 210, 211, 212, 214, 216, 217, 218, 219, 220, 221, 223, 224, 225, 228, 229, 230, 231, 232, 233, 234, 235, 238, 239, 240, 243, 244, 245, 246, 248, 249, 250, 252, 253, 254, 255, 256, 257, 260, 261, 263, 264, 265, 266, 268, 269, 271, 274, 276, 277, 278, 279, 282, 283, 285, 287, 289, 290, 291, 292, 293, 294, 297, 299, 301, 302, 307, 309, 311, 313, 316, 317, 319, 320, 321, 323, 325, 330, 331, 332, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 345, 346, 347, 348], "branches": [[135, 139], [135, 140], [140, 141], [140, 150], [157, 159], [157, 163], [170, 171], [170, 186], [174, 175], [174, 178], [188, 190], [188, 200], [190, 191], [190, 200], [196, 197], [196, 200], [201, 202], [201, 204], [205, 206], [205, 216], [207, 208], [207, 209], [209, 210], [209, 211], [211, 212], [211, 214], [219, 220], [219, 223], [228, 229], [228, 231], [231, 232], [231, 234], [234, 235], [234, 238], [238, 239], [238, 243], [243, 244], [243, 252], [253, 254], [253, 256], [256, 257], [256, 260], [268, 269], [268, 271], [309, 311], [309, 334], [316, 317], [316, 325], [319, 320], [319, 323], [334, 335], [334, 337], [337, 338], [337, 340], [340, 341], [340, 345], [345, 346], [345, 348]]}
# gained: {"lines": [134, 136, 137, 139, 140, 141, 142, 143, 144, 145, 146, 147, 150, 151, 152, 155, 156, 157, 163, 164, 166, 168, 169, 170, 171, 172, 173, 174, 175, 176, 186, 187, 188, 190, 191, 192, 193, 194, 196, 197, 198, 200, 201, 204, 205, 216, 217, 218, 219, 223, 224, 225, 228, 231, 232, 233, 234, 235, 238, 243, 244, 245, 246, 252, 253, 256, 260, 261, 263, 264, 265, 266, 268, 271, 274, 276, 278, 279, 282, 283, 285, 287, 289, 290, 291, 292, 293, 294, 297, 299, 301, 302, 307, 309, 311, 313, 330, 331, 332, 334, 335, 336, 337, 340, 345, 348], "branches": [[135, 139], [135, 140], [140, 141], [140, 150], [157, 163], [170, 171], [174, 175], [188, 190], [190, 191], [196, 197], [201, 204], [205, 216], [219, 223], [228, 231], [231, 232], [234, 235], [238, 243], [243, 244], [253, 256], [256, 260], [268, 271], [309, 311], [334, 335], [337, 340], [340, 345], [345, 348]]}

import types
import pandas as pd
import pytest
from pathlib import Path

import rdagent.components.coder.data_science.pipeline.eval as eval_mod


class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyQueriedKnowledge:
    def __init__(self, success_map=None, failed_set=None):
        self.success_task_to_knowledge_dict = success_map or {}
        self.failed_task_info_set = failed_set or set()


def make_simple_scen():
    class Scenario:
        debug_path = "debug"
        competition = "comp1"
        metric_name = "Accuracy"

        def real_debug_timeout(self):
            return 5

        def get_scenario_all_desc(self, eda_output=None):
            return "scenario description"

    return Scenario()


def test_evaluate_returns_feedback_from_success_mapping():
    # Prepare target task and queried knowledge that contains a success mapping
    task = DummyTask("my_task_info")
    # Use the actual class from the module to avoid mismatch
    PipelineSingleFeedback = eval_mod.PipelineSingleFeedback
    fb = PipelineSingleFeedback(
        execution="exec",
        return_checking="check",
        code="code",
        error_message="err",
        requires_documentation_search=False,
        final_decision=True,
    )
    # knowledge object with mapping
    knowledge = DummyQueriedKnowledge(success_map={"my_task_info": types.SimpleNamespace(feedback=fb)})

    scen = make_simple_scen()
    evaluator = eval_mod.PipelineCoSTEEREvaluator(scen)
    # Call evaluate and ensure it returns the mapped feedback (early return)
    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=knowledge)
    assert result is fb
    assert result.execution == "exec"
    assert result.final_decision is True


def test_evaluate_returns_skip_feedback_for_failed_task():
    task = DummyTask("failed_task")
    knowledge = DummyQueriedKnowledge(success_map={}, failed_set={"failed_task"})

    scen = make_simple_scen()
    evaluator = eval_mod.PipelineCoSTEEREvaluator(scen)
    result = evaluator.evaluate(target_task=task, implementation=None, gt_implementation=None, queried_knowledge=knowledge)
    # Expect a PipelineSingleFeedback with skip messages
    assert isinstance(result, eval_mod.PipelineSingleFeedback)
    assert "failed too many times" in result.execution
    assert result.final_decision is False
    assert result.requires_documentation_search is None


def test_full_evaluate_flow_triggers_all_checks_and_modifies_wfb(tmp_path, monkeypatch):
    """
    Exercise the main flow of evaluate to hit branches:
    - notebook conversion error branch
    - sample submission detection via trace.log
    - scores.csv missing ensemble -> score_ret_code != 0
    - submission format test returning non-zero exit code
    - documentation search exception handling
    - final modifications to wfb.final_decision and return_checking
    """

    # Setup temp workspace
    workspace = tmp_path / "ws"
    workspace.mkdir()

    # Create trace.log that contains an openat line referencing sample submission
    trace_log = workspace / "trace.log"
    sample_name = "sample_submission.csv"
    trace_log.write_text('openat(3, "somefile")\nopenat(4, "{0}")\n'.format(sample_name))

    # Create a scores.csv that lacks 'ensemble' and has a NaN to test NaN branch
    scores_fp = workspace / "scores.csv"
    df = pd.DataFrame({"Accuracy": [0.9, None]}, index=["modelA", "modelB"])
    df.to_csv(scores_fp)

    # Create a main.py content
    main_code = "print('hello world')\n"

    # Fake FBWorkspace class to satisfy isinstance checks and required methods
    class FakeFBWorkspace:
        def __init__(self, path):
            self.workspace_path = Path(path)
            self.file_dict = {"main.py": main_code}
            self._injected = {}

        def execute(self, env, entry):
            self._last_execute = entry

        def inject_files(self, **kwargs):
            for k, v in kwargs.items():
                self._injected[k] = v
                dest = self.workspace_path / k
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(v)

        def run(self, env, entry):
            # coverage run main.py -> simulate a run with stdout containing no debug timing
            if "coverage run main.py" in entry:
                class R:
                    exit_code = 0

                    def get_truncated_stdout(self_inner):
                        return "Main execution output\n"
                return R()
            elif "submission_format_test.py" in entry:
                class R2:
                    exit_code = 2

                    def get_truncated_stdout(self_inner):
                        return "Submission format failed\n"
                return R2()
            else:
                class R3:
                    exit_code = 0

                    def get_truncated_stdout(self_inner):
                        return "Other run\n"
                return R3()

    # Monkeypatch module-level FBWorkspace symbol to our fake so isinstance checks pass
    monkeypatch.setattr(eval_mod, "FBWorkspace", FakeFBWorkspace)

    # Prepare evaluator with a scenario
    scen = make_simple_scen()
    evaluator = eval_mod.PipelineCoSTEEREvaluator(scen)

    # Monkeypatch get_ds_env to return an env object with conf.running_timeout_period
    class ConfObj:
        running_timeout_period = 100

    class Env:
        conf = ConfObj()

    monkeypatch.setattr(eval_mod, "get_ds_env", lambda *args, **kwargs: Env())
    # get_clear_ws_cmd can be anything
    monkeypatch.setattr(eval_mod, "get_clear_ws_cmd", lambda: "clear_cmd")

    # DS_RD_SETTING: set sample_data_by_LLM False to go into submission branch
    class DummySetting:
        sample_data_by_LLM = False
        enable_notebook_conversion = True
        enable_mcp_documentation_search = True

    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", DummySetting)

    # NotebookConverter: validate_code_format returns an error to trigger nb_conversion_ret_code != 0
    class FakeNotebookConverter:
        def validate_code_format(self, code):
            return "Notebook format error"

        def convert(self, *args, **kwargs):
            raise RuntimeError("Should not be called in this test")

    monkeypatch.setattr(eval_mod, "NotebookConverter", FakeNotebookConverter)

    # remove_eda_part: identity function
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda x: x)

    # T object to return simple templated strings; r() returns the template string
    class DummyT:
        def __init__(self, *args, **kwargs):
            pass

        def r(self, *args, **kwargs):
            return "rendered"

    monkeypatch.setattr(eval_mod, "T", DummyT)

    # get_test_eval returns an object controlling sample submission name and submission checks
    class DummyTestEval:
        def get_sample_submission_name(self, competition):
            return sample_name

        def enabled(self, competition):
            return False

        def is_sub_enabled(self, competition):
            # ensure we go to the 'else' branch and run submission_format_test.py
            return True

        def valid(self, competition, implementation):
            return "valid", 0

    monkeypatch.setattr(eval_mod, "get_test_eval", lambda: DummyTestEval())

    # build_cls_from_json_with_retry should return a PipelineSingleFeedback-like object
    PipelineSingleFeedback = eval_mod.PipelineSingleFeedback
    wfb_initial = PipelineSingleFeedback(
        execution="exec",
        return_checking="init_check",
        code="code",
        error_message="some error occurred",
        requires_documentation_search=True,
        final_decision=True,
    )

    monkeypatch.setattr(
        eval_mod,
        "build_cls_from_json_with_retry",
        lambda *args, **kwargs: wfb_initial,
    )

    # DocAgent should raise on construction to hit exception handling branch
    monkeypatch.setattr(eval_mod, "DocAgent", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("doc agent failed")))

    # Prepare an implementation workspace object (FakeFBWorkspace)
    impl = FakeFBWorkspace(workspace)

    # Call evaluate
    result_wfb = evaluator.evaluate(target_task=DummyTask("taskX"), implementation=impl, gt_implementation=None, queried_knowledge=None)

    # After evaluation, because nb conversion failed, scores missing ensemble, submission failing and sample submission opened,
    # final_decision should be False and return_checking should contain messages about these failures.
    assert isinstance(result_wfb, PipelineSingleFeedback)
    assert result_wfb.final_decision is False
    # Check that return_checking has been augmented with messages about failures
    assert ("Submission file check failed" in result_wfb.return_checking) or ("Sample submission file check failed" in result_wfb.return_checking) or ("Notebook format error" in result_wfb.return_checking) or ("scores.csv" in result_wfb.return_checking)
