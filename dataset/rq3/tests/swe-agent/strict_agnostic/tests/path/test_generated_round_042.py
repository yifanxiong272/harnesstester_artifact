import pytest
from types import SimpleNamespace
from pathlib import Path
import sweagent.run.run_batch as run_batch


def test_set_default_output_dir_with_config_and_model_round_042(monkeypatch):
    """When output_dir is DEFAULT and a config file and agent.model.id exist,
    the method should build a path using the config file stem and the model id.
    """
    # Make getpass.getuser deterministic
    monkeypatch.setattr(run_batch.getpass, "getuser", lambda: "alice")

    # Prepare a minimal self-like object with the attributes the method needs
    self_obj = SimpleNamespace(
        output_dir=Path("DEFAULT"),
        instances=SimpleNamespace(id="src1"),
        agent=SimpleNamespace(model=SimpleNamespace(id="modelX")),
        _config_files=["/tmp/conf.yaml"],
        suffix="suf",
    )

    # Call the class method as an unbound function with our fake self
    run_batch.RunBatchConfig.set_default_output_dir(self_obj)

    # Expected path: TRAJECTORY_DIR / user / f"{config_stem}__{model_id}___{source_id}{suffix}"
    expected = (
        run_batch.TRAJECTORY_DIR
        / "alice"
        / f"{Path('/tmp/conf.yaml').stem}__modelX___src1__suf"
    )

    assert self_obj.output_dir == expected


def test_set_default_output_dir_no_config_model_unknown_round_042(monkeypatch):
    """When no _config_files are present and agent.model is missing,
    the method should fall back to "no_config" and model_id "unknown".
    """
    monkeypatch.setattr(run_batch.getpass, "getuser", lambda: "bob")

    # Prepare self-like object without _config_files and without agent.model
    self_obj = SimpleNamespace(
        output_dir=Path("DEFAULT"),
        instances=SimpleNamespace(id="src2"),
        agent=SimpleNamespace(),  # missing .model -> AttributeError in access
        # no _config_files attribute to trigger default
        suffix="",
    )

    run_batch.RunBatchConfig.set_default_output_dir(self_obj)

    expected = run_batch.TRAJECTORY_DIR / "bob" / f"no_config__unknown___src2"

    assert self_obj.output_dir == expected
