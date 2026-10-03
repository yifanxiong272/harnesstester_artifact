def test_probe_001(tmp_path, monkeypatch):
    # Imports scoped inside the test to limit global footprint
    import rdagent.components.coder.data_science.share.eval as eval_mod
    from pathlib import Path
    import pandas as pd

    # 1) Prepare deterministic workspace with a non-empty models/ folder
    ws = tmp_path
    models_dir = ws / "models"
    models_dir.mkdir()
    (models_dir / "m.bin").write_text("model-binary")

    # Create 'before' files
    submission_before = "submission_before_contents"
    scores_before = "id,val\n1,0.1\n2,0.2\n"
    (ws / "submission.csv").write_text(submission_before)
    (ws / "scores.csv").write_text(scores_before)

    # 2) Fake implementation.execute behavior per activation conditions
    class FakeImpl:
        def __init__(self, workspace_path: Path):
            self.workspace_path = workspace_path
            self.all_codes = "print('dummy')"

        def execute(self, env, entry):
            # Use the real get_clear_ws_cmd from the module to compare
            clear_cmd = eval_mod.get_clear_ws_cmd(stage="before_inference")
            if entry == clear_cmd:
                # deterministically remove both files
                for fn in ("submission.csv", "scores.csv"):
                    p = self.workspace_path / fn
                    if p.exists():
                        p.unlink()
                return "cleared"
            if entry == "python main.py":
                # recreate both files with different contents
                (self.workspace_path / "submission.csv").write_text("submission_after_contents")
                (self.workspace_path / "scores.csv").write_text("id,val\n1,0.3\n2,0.4\n")
                return "generated"
            return ""

    impl = FakeImpl(ws)

    # 3) Monkeypatch noisy/external helpers to deterministic stand-ins
    # Ensure the environment builder is trivial and deterministic
    monkeypatch.setattr(eval_mod, "get_ds_env", lambda **kwargs: {"env": True})
    # remove_eda_part should be identity for our deterministic stdout
    monkeypatch.setattr(eval_mod, "remove_eda_part", lambda s: s)
    # T(...) should return an object with r() returning a deterministic string
    class DummyT:
        def __init__(self, arg):
            self.arg = arg
        def r(self, **kwargs):
            return "DUMMY_PROMPT"
    monkeypatch.setattr(eval_mod, "T", DummyT)

    # Build a minimal csfb-like object; evaluate only needs .return_checking to exist and be mutable
    class CSFB:
        def __init__(self):
            self.return_checking = ""
    def fake_build_cls(cls, system_prompt=None, user_prompt=None):
        return CSFB()
    monkeypatch.setattr(eval_mod, "build_cls_from_json_with_retry", fake_build_cls)

    # Force high-level checking as required by the probe
    # Use raising=False to allow DS_RD_SETTING to be a simple object or namespace
    monkeypatch.setattr(eval_mod.DS_RD_SETTING, "model_dump_check_level", "high", raising=False)

    # 4) Prepare a fake 'self' to call the unbound evaluate function
    class FakeSelf:
        pass
    fake_self = FakeSelf()
    fake_self.data_type = "full"
    class Scen:
        pass
    fake_self.scen = Scen()
    fake_self.scen.competition = "dummy_comp"
    fake_self.scen.debug_path = "dummy_debug"

    # 5) Call the public entrypoint function unbound, passing our fake self and workspace
    # Signature: evaluate(self, target_task: Task, implementation: FBWorkspace, gt_implementation: FBWorkspace, ...)
    csfb = eval_mod.ModelDumpEvaluator.evaluate(fake_self, None, impl, None)

    # 6) Primary behavioral oracle: both change messages must be present in return_checking
    assert csfb is not None
    rc = csfb.return_checking or ""
    # Check that the implementation reported the scores.csv change
    assert "[Error] The content of scores.csv has changed" in rc, f"scores message missing; got: {rc!r}"
    # Check that the implementation reported the submission.csv change
    assert "The content of submission.csv has changed" in rc, f"submission message missing; got: {rc!r}"
