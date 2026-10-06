def test_probe_001(tmp_path):
    import types
    from pathlib import Path
    import rdagent.components.coder.data_science.share.eval as eval_mod

    # Prepare deterministic contents
    scores_before = "id,value\n0,0.1\n1,0.2\n"
    scores_after = "id,value\n0,0.9\n1,0.8\n"
    submission_before = "col\nA\nB\n"
    submission_after = "col\nC\nD\n"

    # Create workspace structure
    workspace = tmp_path / "ws"
    workspace.mkdir()
    models_dir = workspace / "models"
    models_dir.mkdir()
    # ensure non-empty models folder
    (models_dir / "m.pkl").write_text("dummy")

    # Write initial files
    (workspace / "scores.csv").write_text(scores_before)
    (workspace / "submission.csv").write_text(submission_before)

    # Minimal FBWorkspace-like mock that implements the execute contract used by evaluate
    class FBWorkspaceMock:
        def __init__(self, workspace_path: Path):
            self.workspace_path = Path(workspace_path)
            self.all_codes = "print('code')"
            self._calls = 0

        def execute(self, env=None, entry=None):
            # First call: clear (remove) the csv files
            self._calls += 1
            if self._calls == 1:
                for fname in ("submission.csv", "scores.csv"):
                    p = self.workspace_path / fname
                    if p.exists():
                        p.unlink()
                return "cleared"
            # Second call: simulate running main.py and re-producing changed csv files
            if self._calls == 2:
                (self.workspace_path / "scores.csv").write_text(scores_after)
                (self.workspace_path / "submission.csv").write_text(submission_after)
                return "stdout: done"
            return ""

    impl = FBWorkspaceMock(workspace)

    # Monkeypatch module-level helpers and settings used by evaluate to deterministic no-ops/controlled behavior
    # get_clear_ws_cmd(stage=...) -> returns a predictable string
    eval_mod.get_clear_ws_cmd = lambda stage="before_inference": "clear_cmd"
    # get_ds_env should accept kwargs and return a dummy env object
    eval_mod.get_ds_env = lambda **kwargs: object()
    # remove_eda_part should be identity for deterministic stdout
    eval_mod.remove_eda_part = lambda s: s
    # Replace DS_RD_SETTING with a simple namespace and set model_dump_check_level to 'high'
    eval_mod.DS_RD_SETTING = types.SimpleNamespace(
        model_dump_check_level="high",
        local_data_path="/tmp/local_data_path",
        full_timeout=1,
        debug_timeout=1,
    )

    # build_cls_from_json_with_retry should deterministically return a CoSTEERSingleFeedback-like instance
    def _build_dummy_csfb(cls, system_prompt=None, user_prompt=None):
        # create instance without invoking constructor
        inst = object.__new__(eval_mod.CoSTEERSingleFeedback)
        # ensure attribute used by evaluate exists
        inst.return_checking = ""
        return inst

    eval_mod.build_cls_from_json_with_retry = _build_dummy_csfb

    # Construct an evaluator instance without running its __init__ (unknown signature); set required attributes
    EvaluatorCls = eval_mod.ModelDumpEvaluator
    evaluator = object.__new__(EvaluatorCls)
    evaluator.scen = types.SimpleNamespace(competition="comp", debug_path="/debug_path")
    evaluator.data_type = "debug"
    evaluator.all_codes = "codes"

    # Call the evaluated entrypoint
    csfb = evaluator.evaluate(target_task=None, implementation=impl, gt_implementation=None)

    # Primary behavioral assertions (oracle):
    rc = getattr(csfb, "return_checking", None)
    assert isinstance(rc, str) and rc, "return_checking must be a non-empty string"

    # Must contain both the scores error marker and the submission error marker
    assert "[Error] The content of scores.csv has changed." in rc, "scores change marker missing"
    assert "[Error] The content of submission.csv has changed." in rc, "submission change marker missing"

    # Scores diagnostic must include the explicit Before/After contents (strong invariant)
    assert "Before:" in rc and "After:" in rc, "Before/After markers for scores not present"
    assert scores_before.strip() in rc, "scores before content not included in diagnostics"
    assert scores_after.strip() in rc, "scores after content not included in diagnostics"
