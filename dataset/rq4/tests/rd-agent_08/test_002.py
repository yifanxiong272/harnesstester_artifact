import importlib
from pathlib import Path


def test_probe_001(tmp_path, monkeypatch):
    """Under model_dump_check_level == 'high', if only submission.csv changes (scores.csv unchanged),
    the evaluator MUST report the submission.csv change in csfb.return_checking.

    This test constructs a deterministic workspace and a FakeWorkspace.execute that simulates
    the clear step and the 'python main.py' run producing the required files with controlled contents.
    """

    # Import only the declared public entrypoint module and symbol
    eval_mod = importlib.import_module("rdagent.components.coder.data_science.share.eval")
    ModelDumpEvaluator = eval_mod.ModelDumpEvaluator

    # Prepare deterministic workspace layout
    ws = tmp_path / "workspace"
    ws.mkdir()
    models = ws / "models"
    models.mkdir()
    # ensure models/ is non-empty (satisfy initial model-folder check)
    (models / "model.bin").write_text("dummy model")

    # Initial artifact contents (pre-run)
    submission_before = "submission_old_v1"
    scores_csv_text = "id,score\n0,0.5\n"
    (ws / "submission.csv").write_text(submission_before)
    (ws / "scores.csv").write_text(scores_csv_text)

    # Prepare a clear-workspace marker and monkeypatch helper functions used by evaluate
    clear_marker = object()
    monkeypatch.setattr(eval_mod, "get_clear_ws_cmd", lambda stage=None: clear_marker)
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda *a, **kw: {"_env": True})
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s)

    # Configure DS_RD_SETTING to force 'high' checking level and provide minimal other attributes
    class _S:
        pass

    ds = _S()
    ds.model_dump_check_level = "high"
    ds.local_data_path = "data"
    ds.full_timeout = 1
    ds.debug_timeout = 1
    monkeypatch.setattr(eval_mod, "DS_RD_SETTING", ds)

    # Provide a fake build_cls_from_json_with_retry that returns a mutable object with return_checking
    class FakeCSFB:
        def __init__(self):
            # Start with an empty or placeholder return_checking to allow the evaluated code to append to it
            self.return_checking = ""

    def fake_build(cls, system_prompt=None, user_prompt=None):
        return FakeCSFB()

    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build)

    # Fake implementation (FBWorkspace-like) that reacts to clear_marker and 'python main.py'
    class FakeWorkspace:
        def __init__(self, path: Path):
            self.workspace_path = path
            self.all_codes = "print('code')"

        def execute(self, env=None, entry=None):
            # Clear step: remove the two artifact files if present
            if entry is clear_marker:
                for fname in ("submission.csv", "scores.csv"):
                    p = self.workspace_path / fname
                    if p.exists():
                        p.unlink()
                return "cleared"
            # Main run: write a new submission.csv (different) and write scores.csv identical to before
            if entry == "python main.py":
                (self.workspace_path / "submission.csv").write_text("submission_new_v2")
                # write scores identical to the pre-run snapshot
                (self.workspace_path / "scores.csv").write_text(scores_csv_text)
                return "program stdout"
            return ""

    impl = FakeWorkspace(ws)

    # Minimal Scenario-like object required by ModelDumpEvaluator.__init__
    class DummyScenario:
        def __init__(self):
            self.competition = "comp"
            self.debug_path = "dbg"

    scen = DummyScenario()
    evaluator = ModelDumpEvaluator(scen, data_type="sample")

    # Call the target entrypoint
    csfb = evaluator.evaluate(target_task=None, implementation=impl, gt_implementation=None)

    # Primary behavioral oracle: the human-facing diagnostics must mention the submission.csv change
    rc = csfb.return_checking or ""
    rc_low = rc.lower()
    assert "submission.csv" in rc_low and "changed" in rc_low, (
        "Expected return_checking to mention that submission.csv changed when model_dump_check_level is 'high',\n"
        f"but got: {rc!r}"
    )
