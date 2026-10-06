import importlib
from types import SimpleNamespace
from pathlib import Path

def test_probe_001(tmp_path):
    """
    Probe: when the submission-format test process returns a non-zero exit code but scores.csv is valid,
    evaluate() should set final_decision to False and include 'Submission file check failed.' in return_checking.

    This test constructs a minimal evaluator instance and a deterministic fake implementation (workspace).
    build_cls_from_json_with_retry is monkeypatched to return a feedback-like object whose return_checking is None
    to surface the hypothesized TypeError bug; if the code is correct it should overwrite/append and the
    final object will contain the diagnostic and final_decision False.
    """

    # Import target module and get class
    mod = importlib.import_module("rdagent.components.coder.data_science.pipeline.eval")
    EvaluatorCls = mod.PipelineCoSTEEREvaluator

    # Minimal scen object required by evaluate
    scen = SimpleNamespace(
        metric_name="accuracy",
        competition="comp",
        get_scenario_all_desc=lambda: "desc",
    )

    # Minimal Task-like object
    task = SimpleNamespace(get_task_information=lambda: "task-1")

    # Fake implementation that acts like FBWorkspace for the exercised entrypoints
    class FakeImpl:
        def __init__(self, workspace_path: Path):
            self.workspace_path = workspace_path
            self.file_dict = {"main.py": "print('hello')"}

        def inject_files(self, **kwargs):
            # keep a record; evaluate will later call execute_ret_code which doesn't inspect these
            self.file_dict.update(kwargs)

        def execute(self, env, entry: str):
            # emulate rm then creation of scores.csv on running main.py
            if entry.startswith("rm "):
                # remove possible files deterministically
                for fn in ("submission.csv", "scores.csv"):
                    p = self.workspace_path / fn
                    if p.exists():
                        p.unlink()
                return "removed"
            if entry == "python main.py":
                # produce a valid scores.csv with index containing 'ensemble' and a single column equal to scen.metric_name
                content = ",accuracy\nensemble,0.5\n"
                fp = self.workspace_path / "scores.csv"
                fp.write_text(content)
                return "main executed"
            return ""

        def execute_ret_code(self, env, entry: str):
            # Simulate a failing submission-format test: non-zero exit code
            return ("Submission check output: failing", 2)

    # Monkeypatch get_ds_env to a minimal object with conf attribute
    original_get_ds_env = getattr(mod, "get_ds_env", None)
    mod.get_ds_env = lambda: SimpleNamespace(conf=SimpleNamespace())

    # Monkeypatch build_cls_from_json_with_retry to return a feedback-like object
    original_builder = getattr(mod, "build_cls_from_json_with_retry", None)

    def fake_builder(cls, system_prompt=None, user_prompt=None, init_kwargs_update_func=None):
        # Intentionally create a feedback object whose return_checking is None to surface concatenation bugs
        fb = SimpleNamespace()
        fb.final_decision = True
        fb.return_checking = None
        return fb

    mod.build_cls_from_json_with_retry = fake_builder

    # Construct evaluator instance and inject scen
    evaluator = object.__new__(EvaluatorCls)
    evaluator.scen = scen

    impl = FakeImpl(tmp_path)

    # Execute the evaluator. If the target code has the hypothesized bug (return_checking is None),
    # this call will raise (TypeError) when trying to append into None; otherwise it should return an object
    # we can assert on.
    try:
        feedback = evaluator.evaluate(task, impl, None, None)
    finally:
        # restore patched symbols to avoid side effects in the test process
        if original_get_ds_env is not None:
            mod.get_ds_env = original_get_ds_env
        if original_builder is not None:
            mod.build_cls_from_json_with_retry = original_builder

    # Primary oracle: the evaluator must mark final_decision False and include the submission failure diagnostic
    assert hasattr(feedback, "final_decision"), "feedback missing final_decision"
    assert feedback.final_decision is False, "Expected final_decision to be False when submission check fails"
    assert feedback.return_checking is not None, "return_checking should be a string containing diagnostics"
    assert "Submission file check failed." in feedback.return_checking, (
        "Expected diagnostic 'Submission file check failed.' in return_checking when submission check returns non-zero"
    )
