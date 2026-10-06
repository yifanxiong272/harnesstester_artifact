import io
from types import SimpleNamespace
from pathlib import Path
import pytest

from rdagent.components.coder.data_science.share import eval as eval_mod
from rdagent.components.coder.data_science.share.eval import ModelDumpEvaluator, CoSTEERSingleFeedback
import pandas as pd


def test_probe_001(tmp_path):
    """
    Probe: when the workspace run produces scores.csv as an empty (zero-byte) file,
    evaluate(...) should not raise pandas.errors.EmptyDataError but instead return
    a CoSTEERSingleFeedback with final_decision == False.
    """

    # Prepare workspace with required pre-run artifacts
    ws = tmp_path / "workspace"
    ws.mkdir()
    models_dir = ws / "models"
    models_dir.mkdir()
    # create a regular file inside models/ so the "not empty" check passes
    (models_dir / "model.bin").write_text("dummy")

    # initial (pre-run) non-empty submission.csv and scores.csv
    (ws / "submission.csv").write_text("id,value\n1,0.5\n")
    (ws / "scores.csv").write_text("id,score\n1,0.5\n")

    # Dummy workspace implementing the execute contract used by evaluate
    class DummyWorkspace:
        def __init__(self, path: Path):
            self.workspace_path = path
            self.all_codes = ""

        def execute(self, env=None, entry=None):
            # clear workspace: remove submission.csv and scores.csv
            if entry == "CLEAR_CMD":
                for f in ["submission.csv", "scores.csv"]:
                    p = self.workspace_path / f
                    if p.exists():
                        p.unlink()
                return "cleared"
            if entry == "python main.py":
                # create a valid submission.csv
                (self.workspace_path / "submission.csv").write_text("id,value\n1,0.5\n")
                # create scores.csv as an empty zero-byte file
                open(self.workspace_path / "scores.csv", "wb").close()
                return "inference stdout"
            # default deterministic response
            return ""

    dummy_impl = DummyWorkspace(ws)

    # Minimal evaluator-like object that will act as `self` in the bound method
    evaluator_self = SimpleNamespace(
        data_type="debug",  # choose debug to avoid using DS_RD_SETTING.local_data_path
        scen=SimpleNamespace(debug_path=str(ws), competition="comp"),
        all_codes="dummy_code",
    )

    # Monkeypatch module helpers to deterministic behavior
    # get_clear_ws_cmd should return the exact string our DummyWorkspace.execute expects
    eval_mod.get_clear_ws_cmd = lambda stage=None: "CLEAR_CMD"
    # get_ds_env is not used in our DummyWorkspace but patch to a no-op
    eval_mod.get_ds_env = lambda *args, **kwargs: {"env": "dummy"}
    # remove_eda_part should be identity for stdout processing
    eval_mod.remove_eda_part = lambda s: s
    # build_cls_from_json_with_retry should return a CoSTEERSingleFeedback (used if pd.read_csv succeeds)
    eval_mod.build_cls_from_json_with_retry = lambda cls, **kwargs: CoSTEERSingleFeedback(
        execution="mock", return_checking="mock", code="mock", final_decision=False
    )

    # Now invoke the target entrypoint. We expect either a return of CoSTEERSingleFeedback
    # with final_decision False, or (if buggy) an uncaught pandas.errors.EmptyDataError.
    try:
        result = ModelDumpEvaluator.evaluate(evaluator_self, None, dummy_impl, None)
    except pd.errors.EmptyDataError as exc:
        pytest.fail(f"ModelDumpEvaluator.evaluate raised pandas.EmptyDataError: {exc}")

    # Primary behavioral oracle: must return a CoSTEERSingleFeedback with final_decision == False
    assert isinstance(result, CoSTEERSingleFeedback), f"expected CoSTEERSingleFeedback, got {type(result)!r}"
    assert getattr(result, "final_decision", True) is False, "expected final_decision == False"
