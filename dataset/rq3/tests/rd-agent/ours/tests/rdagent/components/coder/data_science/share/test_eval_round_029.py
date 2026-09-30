import importlib
import sys
import types
from types import SimpleNamespace
from pathlib import Path
import builtins

import pytest


def make_fake_csfb(**kwargs):
    # simple container to mimic CoSTEERSingleFeedback-like object
    obj = SimpleNamespace()
    obj.execution = kwargs.get("execution", None)
    obj.return_checking = kwargs.get("return_checking", None)
    obj.code = kwargs.get("code", None)
    obj.final_decision = kwargs.get("final_decision", None)
    return obj


@pytest.fixture(autouse=True)
def import_eval_module(monkeypatch, tmp_path):
    """Import the module under test and patch external collaborators to deterministic fakes.

    This fixture yields the imported module object as an attribute on sys.modules entry so tests
    can import it freshly if needed. It also monkeypatches many globals the tested function
    resolves at runtime.
    """
    mod_name = "rdagent.components.coder.data_science.share.eval"
    eval_mod = importlib.import_module(mod_name)

    # Patch CoSTEERSingleFeedback constructor used to build returned objects
    monkeypatch.setattr(eval_mod, "CoSTEERSingleFeedback", lambda **kwargs: make_fake_csfb(**kwargs))

    # Patch utility functions to deterministic no-ops or simple behavior
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda **kwargs: {"env": True})
    monkeypatch.setattr(eval_mod, "get_clear_ws_cmd", lambda stage=None: "clear-cmd")
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s)

    # Provide deterministic build_cls_from_json_with_retry
    monkeypatch.setattr(
        eval_mod,
        "build_cls_from_json_with_retry",
        lambda cls, system_prompt=None, user_prompt=None: make_fake_csfb(
            execution="ok", return_checking="ok", code="ok", final_decision=True
        ),
    )

    # Provide a simple DS_RD_SETTING namespace with attributes used
    fake_setting = SimpleNamespace(local_data_path=str(tmp_path / "local_data"), model_dump_check_level="low")
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", fake_setting)

    # Patch template loader T to a simple callable returning .r() -> value
    class FakeT:
        def __init__(self, v):
            self.v = v

        def r(self, **kwargs):
            # return whatever was configured as value
            return self.v

    monkeypatch.setattr(eval_mod, "T", lambda spec: FakeT(str(tmp_path / "input")))

    # Ensure dynamic import of FileTreeGenerator inside function finds our fake module
    ftmod_name = "rdagent.scenarios.data_science.scen.utils"
    ftmod = types.ModuleType(ftmod_name)

    class FileTreeGenerator:
        def __init__(self, allowed_paths=None):
            self.allowed_paths = allowed_paths

        def generate_tree(self, base_path):
            # return a deterministic tree representation for testing
            return {"generated_from": str(base_path), "allowed": sorted([str(p) for p in (self.allowed_paths or [])])}

    ftmod.FileTreeGenerator = FileTreeGenerator
    sys.modules[ftmod_name] = ftmod

    return eval_mod


def _make_evaluator(eval_mod, scen_competition="comp", scen_debug_path=None, data_type="debug"):
    # Create an evaluator instance without invoking its real constructor
    ev = object.__new__(eval_mod.ModelDumpEvaluator)
    # scen must provide attributes referenced in the method
    scen = SimpleNamespace(
        competition=scen_competition,
        debug_path=str(scen_debug_path) if scen_debug_path is not None else "debug_path",
        real_full_timeout=lambda: 1,
        real_debug_timeout=lambda: 1,
    )
    ev.scen = scen
    ev.data_type = data_type
    return ev


def _make_implementation(workspace_path: Path, stdout_for_inference: str = "inference-output"):
    # Simple implementation-like object with workspace_path and execute method
    def execute(env=None, entry=None):
        # Return stdout only when calling inference entry (string contains 'inference')
        if isinstance(entry, str) and "inference" in entry:
            return stdout_for_inference
        return ""

    impl = SimpleNamespace(workspace_path=workspace_path, execute=execute, all_codes="# code")
    return impl


def test_model_folder_missing_round_029(import_eval_module, tmp_path):
    """If the models folder does not exist or is empty, evaluate should return an error feedback.

    This exercises the branch at the top of the evaluator that checks for the existence
    (and non-emptiness) of the models subfolder.
    """
    eval_mod = import_eval_module

    # Prepare evaluation environment where models folder is absent
    ws = tmp_path / "workspace1"
    ws.mkdir()
    implementation = _make_implementation(ws)

    # Build evaluator with debug data_type (so data_source_path will use scen.debug_path)
    evaluator = _make_evaluator(eval_mod, scen_debug_path=str(tmp_path / "data_source"), data_type="debug")

    # Call evaluate; models folder does not exist -> early return
    result = eval_mod.ModelDumpEvaluator.evaluate(evaluator, target_task=None, implementation=implementation, gt_implementation=None)

    # Assert it returns the fake CoSTEERSingleFeedback and contains the expected message
    assert hasattr(result, "final_decision")
    assert result.final_decision is False
    assert isinstance(result.execution, str) and "Model folder" in result.execution


def test_missing_submission_or_scores_round_029(import_eval_module, tmp_path, monkeypatch):
    """When models exist but submission.csv or scores.csv are missing, evaluate should return an error mentioning the missing file.

    This covers the code path that proceeds past model folder check, runs the model, parses trace.log,
    and then checks for presence of submission/scores, returning early if absent.
    """
    eval_mod = import_eval_module

    # Setup workspace with models (so initial model folder check passes)
    ws = tmp_path / "workspace2"
    ws.mkdir()
    models_dir = ws / "models"
    models_dir.mkdir()
    # create a dummy model file so model_folder.iterdir() yields something
    (models_dir / "model.bin").write_text("binary")

    # Create trace.log referencing files under the input path
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    # place a referenced file under input to make the path resolution consistent
    (input_dir / "data.txt").write_text("d")

    # Trace line should include the absolute path to the input file so regex and startswith match
    abs_input = str((input_dir / "data.txt").resolve())
    trace_line = f'openat(AT_FDCWD, "{abs_input}", O_RDONLY) = 5\n'
    (ws / "trace.log").write_text(trace_line)

    implementation = _make_implementation(ws, stdout_for_inference="stdout-text")

    # Build evaluator; use debug so data_source_path == scen.debug_path
    evaluator = _make_evaluator(eval_mod, scen_competition="comp", scen_debug_path=str(tmp_path / "data_source"), data_type="debug")

    # Ensure T().r() returns the input_dir path used in trace
    class FakeT2:
        def __init__(self, v):
            self.v = v

        def r(self, **kwargs):
            return str(input_dir)

    monkeypatch.setattr(eval_mod, "T", lambda spec: FakeT2(str(input_dir)))

    # Ensure our dynamic FileTreeGenerator module remains available (fixture imported it already), but also
    # verify DS_RD_SETTING has local_data_path set to a known value
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", SimpleNamespace(local_data_path=str(tmp_path / "local_data"), model_dump_check_level="low"))

    # Do NOT create submission.csv or scores.csv so the loop for files triggers the missing-file branch

    result = eval_mod.ModelDumpEvaluator.evaluate(evaluator, target_task=None, implementation=implementation, gt_implementation=None)

    assert hasattr(result, "final_decision")
    assert result.final_decision is False
    # Should mention a missing file name (either submission.csv or scores.csv)
    assert isinstance(result.execution, str)
    assert ("submission.csv" in result.execution) or ("scores.csv" in result.execution)
