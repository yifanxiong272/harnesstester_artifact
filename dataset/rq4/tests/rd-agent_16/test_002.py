import io
import types
from pathlib import Path

def test_probe_001(tmp_path):
    """
    Probe: When scores.csv contains undecodable bytes, evaluate(...) should not crash;
    it should return a feedback-like object with final_decision == False and an explanatory message
    containing the phrase 'in checking the scores.csv file'. This test constructs a deterministic
    FBWorkspace-like stub and triggers a UnicodeDecodeError path in pandas.read_csv.
    """

    # Import only the declared module/class entrypoint
    import rdagent.components.coder.data_science.workflow.eval as eval_mod

    # Prepare a temporary workspace with an undecodable scores.csv
    ws = tmp_path / "workspace"
    ws.mkdir()
    score_path = ws / "scores.csv"
    # Write bytes that are invalid UTF-8 so Path.read_text() will raise UnicodeDecodeError
    score_path.write_bytes(b"\xff\xff\xff\xff")

    # Ensure eval tests file exists (module expects DIRNAME / eval_tests / submission_format_test.txt)
    eval_tests_dir = eval_mod.DIRNAME / "eval_tests"
    eval_tests_dir.mkdir(parents=True, exist_ok=True)
    (eval_tests_dir / "submission_format_test.txt").write_text("# dummy submission format test")

    # Build deterministic implementation stub (FBWorkspace-like)
    class ImplStub:
        def __init__(self, workspace_path: Path):
            self.workspace_path = workspace_path
            # include keys that the evaluate implementation may access
            self.file_dict = {
                "main.py": "print('hello')",
                "spec/workflow.md": "spec",
            }

        def execute(self, env=None, entry=None):
            # deterministic, do not invoke processes
            return "exec-output"

        def execute_ret_code(self, env=None, entry=None):
            # return tuple (stdout, ret_code)
            return ("submission-check-ok", 0)

        def inject_files(self, **kw):
            # emulate writing injected test files into file_dict
            for k, v in kw.items():
                self.file_dict[k] = v

    impl = ImplStub(ws)

    # Minimal scen object expected by evaluate (self.scen)
    scen = types.SimpleNamespace(
        competition="comp",
        metric_name="metric_x",
        get_scenario_all_desc=lambda: "scenario-desc",
    )

    # Minimal target_task stub
    target_task = types.SimpleNamespace(get_task_information=lambda: "task-info")

    # Build a simple 'self' object carrying scen
    self_obj = types.SimpleNamespace(scen=scen)

    # Monkeypatch pandas.read_csv to deterministically raise UnicodeDecodeError
    orig_read_csv = eval_mod.pd.read_csv

    def fake_read_csv(*args, **kwargs):
        # Raise UnicodeDecodeError like a real failed decode
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    eval_mod.pd.read_csv = fake_read_csv

    # Monkeypatch build_cls_from_json_with_retry to avoid external behavior and to return a simple feedback-like object
    class SimpleFeedback:
        def __init__(self):
            # default values; evaluate(...) will mutate these
            self.final_decision = True
            self.return_checking = ""

    orig_builder = eval_mod.build_cls_from_json_with_retry

    def fake_builder(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        return SimpleFeedback()

    eval_mod.build_cls_from_json_with_retry = fake_builder

    try:
        # Call the class method function object directly with our fabricated self
        func = getattr(eval_mod.WorkflowGeneralCaseSpecEvaluator, "evaluate")

        # Call and assert the oracle. If the implementation is buggy and raises, the test will error here
        wfb = func(self_obj, target_task, impl, None, None)

        # Primary oracle: must not crash; must return feedback-like object with final_decision False
        assert hasattr(wfb, "final_decision"), "returned object lacks final_decision attr"
        assert hasattr(wfb, "return_checking"), "returned object lacks return_checking attr"
        assert wfb.final_decision is False, "Evaluator must mark final_decision False when scores.csv cannot be decoded"
        assert "in checking the scores.csv file" in wfb.return_checking, (
            "Evaluator must include an explanatory message containing 'in checking the scores.csv file'"
        )
    finally:
        # restore patched callables to avoid side effects for other tests
        eval_mod.pd.read_csv = orig_read_csv
        eval_mod.build_cls_from_json_with_retry = orig_builder
