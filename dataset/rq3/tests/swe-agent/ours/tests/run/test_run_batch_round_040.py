import importlib
from types import SimpleNamespace
from pathlib import Path
import pytest


@ pytest.mark.parametrize("user,config_files,suffix,model_id,source_id,expected_config_stem", [
    ("alice", ["config.yaml"], "suf", "modelA", "source123", "config"),
    ("bob", None, "", None, "src987", "no_config"),
])
def test_set_default_output_dir_various_cases_round_040(monkeypatch, tmp_path, user, config_files, suffix, model_id, source_id, expected_config_stem):
    """
    Exercises RunBatchConfig.set_default_output_dir for both:
    - agent with a model.id and an explicit config file (covers the branch that converts config file to its stem,
      and the non-empty suffix path), and
    - agent missing a model (AttributeError) and no _config_files present (covers the fallback to "no_config"
      and the empty-suffix path).

    This test patches module-level TRAJECTORY_DIR and getpass.getuser to be deterministic and avoids importing
    or instantiating the full RunBatchConfig pydantic class by calling the unbound method with a simple
    namespace object that provides only the attributes the method reads or writes.
    """
    # Import the module under test
    run_batch = importlib.import_module("sweagent.run.run_batch")

    # Patch TRAJECTORY_DIR to a deterministic temporary path
    monkeypatch.setattr(run_batch, "TRAJECTORY_DIR", tmp_path)

    # Patch getpass.getuser to return deterministic username
    monkeypatch.setattr(run_batch.getpass, "getuser", lambda: user)

    # Build a minimal 'self' object with the attributes used by the method
    dummy = SimpleNamespace()
    dummy.output_dir = Path("DEFAULT")
    dummy.instances = SimpleNamespace(id=source_id)

    # Provide agent: either with model.id or missing model to trigger AttributeError
    if model_id is not None:
        dummy.agent = SimpleNamespace(model=SimpleNamespace(id=model_id))
    else:
        # Agent exists but has no 'model' attribute to trigger AttributeError when accessed
        dummy.agent = SimpleNamespace()

    # Set up _config_files if provided, otherwise leave it absent to exercise getattr default
    if config_files is not None:
        dummy._config_files = config_files

    # Set suffix attribute (empty string or some value)
    dummy.suffix = suffix

    # Call the unbound method from the class with our lightweight object
    # This avoids constructing the full pydantic RunBatchConfig object
    run_batch.RunBatchConfig.set_default_output_dir(dummy)

    # Determine expected model id text
    expected_model = model_id if model_id is not None else "unknown"

    # Determine expected config_file stem or literal 'no_config'
    if config_files is not None and config_files[0] != "no_config":
        expected_config = expected_config_stem
    else:
        expected_config = "no_config"

    expected_suffix = f"__{suffix}" if suffix else ""

    expected_path = (
        tmp_path
        / user
        / f"{expected_config}__{expected_model}___{source_id}{expected_suffix}"
    )

    assert dummy.output_dir == expected_path


def test_set_default_output_dir_no_change_when_not_default_round_040(monkeypatch, tmp_path):
    """
    Ensure that when output_dir is not Path("DEFAULT") the method does not modify it.
    This covers the early-exit branch when the output_dir is already set.
    """
    run_batch = importlib.import_module("sweagent.run.run_batch")
    monkeypatch.setattr(run_batch, "TRAJECTORY_DIR", tmp_path)
    monkeypatch.setattr(run_batch.getpass, "getuser", lambda: "z")

    dummy = SimpleNamespace()
    dummy.output_dir = Path("/already/set/path")
    # Provide other attributes that would be used if the method executed; they should remain unused
    dummy.instances = SimpleNamespace(id="doesnotmatter")
    dummy.agent = SimpleNamespace(model=SimpleNamespace(id="m"))
    dummy._config_files = ["conf.yaml"]
    dummy.suffix = "x"

    original = dummy.output_dir

    run_batch.RunBatchConfig.set_default_output_dir(dummy)

    # Should remain unchanged
    assert dummy.output_dir == original
