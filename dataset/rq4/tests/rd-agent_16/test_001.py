import importlib
from types import SimpleNamespace
from pathlib import Path


def test_probe_001(tmp_path):
    """
    Probe: if scores.csv decoding fails, evaluate(...) should return a feedback
    (final_decision == False) with a scores.csv diagnostic rather than
    propagating a UnicodeDecodeError from trying to read the raw file.
    """

    # Load the target module and the evaluate function (instance method)
    mod = importlib.import_module("rdagent.components.coder.data_science.pipeline.eval")
    evaluate_fn = getattr(mod.PipelineCoSTEEREvaluator, "evaluate")

    # --- Deterministic monkeypatches for the module collaborators ---
    # Ensure prompt/template helpers are safe and deterministic
    mod.T = lambda *a, **k: SimpleNamespace(r=lambda **kw: "PROMPT")
    # Minimal deterministic environment object with assignable conf
    mod.get_ds_env = lambda: SimpleNamespace(conf=SimpleNamespace(extra_volumes=None))
    # Ensure build returns a simple feedback-like object we can inspect
    def fake_build(*args, **kwargs):
        return SimpleNamespace(final_decision=True, return_checking="")
    mod.build_cls_from_json_with_retry = fake_build

    # Make sure the eval_tests submission_format_test.txt can be read deterministically
    eval_tests_dir = tmp_path / "eval_tests"
    eval_tests_dir.mkdir()
    (eval_tests_dir / "submission_format_test.txt").write_text("# submission format test placeholder\nprint(0)")
    mod.DIRNAME = tmp_path

    # Force pandas.read_csv in the module to raise so the except: block runs
    original_read_csv = mod.pd.read_csv
    mod.pd.read_csv = lambda *a, **k: (_ for _ in ()).throw(ValueError("forced parse failure"))

    # --- Construct fake workspace and path objects to deterministically trigger read_text() failure ---
    class FakeScorePath:
        def exists(self):
            return True

        # When code attempts to include raw file contents it will call read_text()
        def read_text(self, *a, **k):
            # Simulate a decoding failure when trying to get the file text
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    class FakeWorkspacePath:
        def __truediv__(self, other):
            # return a path-like object for any suffix (scores.csv)
            return FakeScorePath()

    # Fake implementation that the evaluator expects (minimal interface)
    class FakeImplementation:
        def __init__(self):
            self.workspace_path = FakeWorkspacePath()
            self.file_dict = {"main.py": "print('hello')"}
            self._injected = {}

        def execute(self, *a, **k):
            # Called to remove files and to run main; deterministic stdout
            return "program stdout"

        def execute_ret_code(self, *a, **k):
            # Called for submission format test; return no error
            return ("submission check output", 0)

        def inject_files(self, **files):
            # store injected files so prompts referencing implementation.file_dict still valid
            self._injected.update(files)

    impl = FakeImplementation()

    # Minimal gt_implementation and queried_knowledge (not used for this probe)
    gt_impl = None

    # Minimal Task-like object
    task = SimpleNamespace(get_task_information=lambda: "task-key-1")

    # Minimal fake self for the unbound evaluate function: provide scen with needed attributes
    fake_self = SimpleNamespace(
        scen=SimpleNamespace(
            competition="comp",
            metric_name="metric",
            get_scenario_all_desc=lambda: "scenario-desc",
        )
    )

    # --- Invocation: call the evaluate function as an unbound function with our fake self ---
    try:
        wfb = evaluate_fn(fake_self, task, impl, gt_impl, None)
    finally:
        # Restore the pandas.read_csv to avoid side effects for other tests
        mod.pd.read_csv = original_read_csv

    # Primary assertions (oracle)
    assert hasattr(wfb, "final_decision"), "Returned object must have final_decision"
    assert hasattr(wfb, "return_checking"), "Returned object must have return_checking"
    assert wfb.final_decision is False, "When scores.csv cannot be parsed/decoded the evaluator should set final_decision to False"
    assert "[Error] in checking the scores.csv file:" in wfb.return_checking, (
        "Evaluator should append the scores.csv read/parse diagnostic to return_checking"
    )
