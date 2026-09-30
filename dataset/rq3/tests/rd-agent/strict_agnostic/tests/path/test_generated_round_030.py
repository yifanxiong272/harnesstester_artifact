import sys
import types
from pathlib import Path
from types import SimpleNamespace
import pytest

# Import the module under test
from rdagent.components.coder.data_science.share import eval as eval_mod


class DummyFBWorkspace:
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.all_codes = "# code"

    def execute(self, env=None, entry=None):
        # Clear workspace command: remove submission.csv and scores.csv
        if entry and "before_inference" in str(entry):
            for f in ("submission.csv", "scores.csv"):
                p = self.workspace_path / f
                if p.exists():
                    p.unlink()
            return "cleared"

        # Main execution: create submission.csv, scores.csv and trace.log
        if entry and "python main.py --inference" in str(entry):
            # create changed submission and scores files
            (self.workspace_path / "submission.csv").write_text("submission_after\nline")
            (self.workspace_path / "scores.csv").write_text("id,value\n1,0.5")
            # create a trace.log that references the input path used by T(...).r()
            input_path = eval_mod.T("scenarios.data_science.share:scen.input_path").r()
            # Make sure the trace references a file under that input_path
            trace_line = f'openat(AT_FDCWD, "{input_path}/train.csv", O_RDONLY) = 5\n'
            (self.workspace_path / "trace.log").write_text(trace_line)
            return "stdout from run"

        # Default: return empty stdout
        return ""


def _install_dummy_filetreegenerator():
    # Provide a dummy module for rdagent.scenarios.data_science.scen.utils with FileTreeGenerator
    mod_name = "rdagent.scenarios.data_science.scen.utils"
    if mod_name in sys.modules:
        return
    m = types.ModuleType(mod_name)

    class FileTreeGenerator:
        def __init__(self, allowed_paths=None):
            self.allowed_paths = allowed_paths or set()

        def generate_tree(self, base_path):
            # Return a deterministic summary of opened files
            return [str(p) for p in sorted(self.allowed_paths)]

    m.FileTreeGenerator = FileTreeGenerator
    sys.modules[mod_name] = m


def _monkeypatch_eval_module(tmp_path):
    # Replace external dependencies in the evaluated module with deterministic stubs
    eval_mod.get_ds_env = lambda extra_volumes=None, running_timeout_period=None: {"env": "dummy"}
    eval_mod.get_clear_ws_cmd = lambda stage=None: f"clear_ws:{stage}"
    eval_mod.remove_eda_part = lambda s: s

    # T(...) stub: returns an object with r() method that yields expected strings
    class TStub:
        def __init__(self, key):
            self.key = key

        def r(self, *args, **kwargs):
            # For input path, return an absolute path inside tmp_path
            if self.key == "scenarios.data_science.share:scen.input_path":
                return str((tmp_path / "abs_input").resolve())
            # For prompts, return simple strings (system) or formatted (user)
            if self.key == ".prompts:dump_model_eval.system":
                return "{\"system\": \"ok\"}"
            if self.key == ".prompts:dump_model_eval.user":
                # emulate receiving kwargs via r(...)
                return "{\"user\": \"ok\"}"
            return ""

    eval_mod.T = TStub

    # build_cls_from_json_with_retry -> return a simple object with return_checking attribute
    def _build(cls, system_prompt=None, user_prompt=None):
        # return a simple namespace acting like CoSTEERSingleFeedback
        return SimpleNamespace(return_checking="", execution="executed", code="code", final_decision=True)

    eval_mod.build_cls_from_json_with_retry = _build

    # Monkeypatch DS_RD_SETTING inside module
    eval_mod.DS_RD_SETTING = SimpleNamespace(local_data_path=str(tmp_path / "data"), model_dump_check_level="high")

    # Provide FileTreeGenerator stub in importable location
    _install_dummy_filetreegenerator()


def _make_evaluator_instance(tmp_path, data_type="full"):
    # Create an evaluator instance bypassing __init__ to set required attributes
    evaluator = eval_mod.ModelDumpEvaluator.__new__(eval_mod.ModelDumpEvaluator)
    # minimal scen
    scen = SimpleNamespace(
        competition="comp",
        debug_path=str(tmp_path / "debug"),
        real_full_timeout=lambda: 1,
        real_debug_timeout=lambda: 1,
    )
    evaluator.scen = scen
    evaluator.data_type = data_type
    return evaluator


def test_missing_model_folder_round_030(tmp_path):
    """When the models folder does not exist or is empty, evaluate should return a CoSTEERSingleFeedback with an error about missing model folder."""
    # prepare environment
    _monkeypatch_eval_module(tmp_path)

    # workspace without models folder
    ws_path = tmp_path / "ws_missing_models"
    ws_path.mkdir()
    impl = DummyFBWorkspace(ws_path)

    evaluator = _make_evaluator_instance(tmp_path, data_type="full")

    # Call evaluate and assert the early return for missing models folder
    result = evaluator.evaluate(target_task=None, implementation=impl, gt_implementation=None)

    assert hasattr(result, "execution")
    assert "Model folder" in result.execution or "models" in result.execution
    assert result.final_decision is False


def test_model_dump_high_change_round_030(tmp_path):
    """When model dump check level is high and both scores and submission content change, the returned return_checking should include the submission changed error."""
    _monkeypatch_eval_module(tmp_path)

    # create workspace with a non-empty models folder
    ws_path = tmp_path / "ws_model"
    ws_path.mkdir()
    (ws_path / "models").mkdir()
    # add a dummy model file to ensure the models folder is non-empty
    (ws_path / "models" / "model.pkl").write_text("model")

    # create initial submission and scores files (before execution)
    (ws_path / "submission.csv").write_text("submission_before\nline")
    (ws_path / "scores.csv").write_text("id,value\n1,0.4")

    impl = DummyFBWorkspace(ws_path)

    evaluator = _make_evaluator_instance(tmp_path, data_type="full")

    # Evaluate: the DummyFBWorkspace.execute will clear the files then write new ones and trace.log
    result = evaluator.evaluate(target_task=None, implementation=impl, gt_implementation=None)

    # The module build returns an object where return_checking was appended with the submission error
    assert hasattr(result, "return_checking")
    # When both scores and submission change, code sets a submission-specific error string
    assert "content of submission.csv has changed" in (result.return_checking or "") or "submission.csv has changed" in (result.return_checking or "")


if __name__ == "__main__":
    pytest.main([__file__])
