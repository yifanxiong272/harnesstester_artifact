import json
from types import SimpleNamespace
from pathlib import Path
import pandas as pd
import rdagent.components.coder.data_science.workflow.eval as mod


def test_probe_001(tmp_path, monkeypatch):
    """
    Boundary: boundary-001

    Purpose: When scores.csv is present with correct model index but wrong column name,
    verify evaluate() does not raise and returns a feedback-like object with final_decision False
    and a readable diagnostic that mentions incorrect column names.
    """

    # --- Prepare a fake workspace with scores.csv ---
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()

    # Create a scores dataframe with index matching model names and column name different from metric
    df = pd.DataFrame({"wrong_metric": [0.1, 0.2]}, index=["model_a", "ensemble"])
    scores_fp = ws_dir / "scores.csv"
    df.to_csv(scores_fp)

    # Create a dummy eval_tests/submission_format_test.txt file that the code will read via DIRNAME
    eval_tests_dir = tmp_path / "eval_tests"
    eval_tests_dir.mkdir()
    (eval_tests_dir / "submission_format_test.txt").write_text("print('submission check')")

    # --- Fake file_dict used by evaluator to determine model files ---
    file_dict = {
        "model_a.py": "# dummy model",
        "main.py": "print('main')",
        "spec/workflow.md": "spec text",
    }

    # --- Fake workspace object implementing the minimal FBWorkspace API used by evaluate() ---
    class FakeWorkspace:
        def __init__(self, workspace_path: Path, file_dict: dict):
            self.workspace_path = Path(workspace_path)
            self.file_dict = dict(file_dict)

        def execute(self, env=None, entry: str = ""):
            # deterministic, no subprocesses
            if entry.startswith("rm "):
                return ""
            if "coverage run main.py" in entry:
                return "coverage run output"
            if entry.startswith("python -m coverage json"):
                return "coverage json output"
            return ""

        def execute_ret_code(self, env=None, entry: str = ""):
            # submission format test returns success to isolate the score-check path
            return ("submission stdout", 0)

        def inject_files(self, **kwargs):
            # Accept injections; evaluator doesn't inspect returned value
            for p, code in kwargs.items():
                # also mirror injected files into file_dict so evaluator can access main.py if needed
                self.file_dict[p] = code

    impl = FakeWorkspace(ws_dir, file_dict)

    # --- Fake target task ---
    class FakeTask:
        def get_task_information(self):
            return "task_identifier"

    target_task = FakeTask()

    # --- Monkeypatch module-level dependencies to deterministic stubs ---
    # 1) get_ds_env -> returns an object with conf.extra_volumes
    def fake_get_ds_env():
        env = SimpleNamespace()
        env.conf = SimpleNamespace()
        env.conf.extra_volumes = {}
        return env

    monkeypatch.setattr(mod, "get_ds_env", fake_get_ds_env, raising=False)

    # 2) DIRNAME -> point to tmp_path so (DIRNAME / 'eval_tests' / ...).read_text() works
    monkeypatch.setattr(mod, "DIRNAME", tmp_path, raising=False)

    # 3) DS_RD_SETTING -> ensure spec_enabled and local_data_path are present
    monkeypatch.setattr(mod, "DS_RD_SETTING", SimpleNamespace(local_data_path=str(tmp_path), spec_enabled=False), raising=False)

    # 4) T -> returns an object with r(...) -> string
    class TStub:
        def __init__(self, *args, **kwargs):
            pass

        def r(self, **kwargs):
            return "rendered prompt"

    def fake_T(key=None):
        return TStub()

    monkeypatch.setattr(mod, "T", fake_T, raising=False)

    # 5) build_cls_from_json_with_retry -> return an instance of the passed-in cls
    #    with return_checking intentionally set to None to exercise the concatenation hazard described in the plan.
    def fake_build_cls_from_json_with_retry(cls, **kwargs):
        # create instance without calling cls.__init__ to avoid unknown constructor requirements
        inst = object.__new__(cls)
        # initial conservative defaults; the hypothesis is that return_checking may be None in some flows
        setattr(inst, "final_decision", True)
        setattr(inst, "return_checking", None)
        # other code may access other attributes; keep minimal
        return inst

    monkeypatch.setattr(mod, "build_cls_from_json_with_retry", fake_build_cls_from_json_with_retry, raising=False)

    # --- Construct evaluator instance without invoking its constructor ---
    EvalCls = mod.WorkflowGeneralCaseSpecEvaluator
    evaluator = object.__new__(EvalCls)
    # attach a minimal scen used by evaluate()
    evaluator.scen = SimpleNamespace(metric_name="accuracy", competition="comp", get_scenario_all_desc=lambda: "desc")

    # Ensure there is no queried_knowledge to take early-return branches
    queried_knowledge = None

    # --- Execute: This is the single behavioral invocation / oracle ---
    result = evaluator.evaluate(target_task, impl, None, queried_knowledge=queried_knowledge)

    # Primary oracle: evaluate must return a feedback-like object (no exception) indicating failure and containing the correct diagnostic
    assert hasattr(result, "final_decision"), "evaluate did not return a feedback-like object"
    assert result.final_decision is False, "Expected final_decision to be False when score columns are incorrect"
    assert "The scores dataframe does not contain the correct column names" in (result.return_checking or ""), (
        "Expected diagnostic about incorrect column names to be present in return_checking"
    )
