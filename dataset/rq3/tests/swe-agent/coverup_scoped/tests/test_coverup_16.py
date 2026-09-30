# file: sweagent/run/run_single.py:68-117
# asked: {"lines": [92, 93, 96, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 116], "branches": [[95, 96]]}
# gained: {"lines": [92, 93, 96, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 116], "branches": [[95, 96]]}

import builtins
from pathlib import Path

import pytest

from sweagent.run.run_single import RunSingleConfig
from sweagent.agent.problem_statement import EmptyProblemStatement
from sweagent.run import run_single as run_single_module
from sweagent.run.common import AutoCorrectSuggestion as ACS


def make_minimal_run_single_instance(config_files):
    """
    Create a RunSingleConfig instance without running full pydantic validation by using
    object.__new__ and setting the minimal internal attributes pydantic expects.
    """
    inst = object.__new__(RunSingleConfig)
    # Minimal pydantic internals to allow attribute setting
    setattr(inst, "__pydantic_fields_set__", set())
    setattr(inst, "__pydantic_private__", {})
    setattr(inst, "__pydantic_extra__", {})
    setattr(inst, "__private_attributes__", {})
    # set required fields
    inst.output_dir = Path("DEFAULT")
    inst.problem_statement = EmptyProblemStatement()
    # agent without a .model attribute to trigger AttributeError in set_default_output_dir
    inst.agent = object()
    # attach _config_files as provided (list with single element)
    inst._config_files = [config_files]
    return inst


def test_set_default_output_dir_with_string_config(monkeypatch, tmp_path):
    # Ensure getuser is stable
    monkeypatch.setattr(run_single_module.getpass, "getuser", lambda: "testuser")
    inst = make_minimal_run_single_instance("no_config")
    assert inst.output_dir == Path("DEFAULT")
    inst.set_default_output_dir()
    # Should have replaced DEFAULT
    assert inst.output_dir != Path("DEFAULT")
    # Build expected tail using values from instance
    user_id = "testuser"
    model_id = "unknown_model"
    problem_id = inst.problem_statement.id
    expected_tail = f"no_config__{model_id}___{problem_id}"
    # last part of path should match expected_tail
    assert inst.output_dir.parts[-1] == expected_tail
    # should include 'trajectories' and user id in path
    assert "trajectories" in inst.output_dir.parts
    assert user_id in inst.output_dir.parts


def test_set_default_output_dir_with_path_config(monkeypatch):
    # Ensure getuser is stable
    monkeypatch.setattr(run_single_module.getpass, "getuser", lambda: "alice")
    cfg_path = Path("/some/place/myconfig.yaml")
    inst = make_minimal_run_single_instance(cfg_path)
    assert inst.output_dir == Path("DEFAULT")
    inst.set_default_output_dir()
    assert inst.output_dir != Path("DEFAULT")
    # config_file should have been converted to stem 'myconfig'
    model_id = "unknown_model"
    problem_id = inst.problem_statement.id
    expected_tail = f"myconfig__{model_id}___{problem_id}"
    assert inst.output_dir.parts[-1] == expected_tail
    # ensure correct username from monkeypatch
    assert "alice" in inst.output_dir.parts


def test_get_auto_correct_suggestions_list_properties():
    ac_list = RunSingleConfig._get_auto_correct()
    # Expect 9 suggestions as defined in the implementation
    assert isinstance(ac_list, list)
    assert len(ac_list) == 9

    # Map originals to suggestions for easy assertions
    orig_map = {a.original: a for a in ac_list}
    # Check entries that should point alternatives
    assert orig_map["model"].alternative == "agent.model.name"
    assert orig_map["agent.model"].alternative == "agent.model.name"
    assert orig_map["model.name"].alternative == "agent.model.name"
    assert orig_map["per_instance_cost_limit"].alternative == "agent.model.per_instance_cost_limit"
    assert orig_map["model.per_instance_cost_limit"].alternative == "agent.model.per_instance_cost_limit"
    assert orig_map["config_file"].alternative == "config"
    assert orig_map["repo.path"].alternative == "env.repo.path"

    # Check entries that should provide help (and not alternative)
    assert orig_map["data_path"].help is not None
    assert orig_map["data_path"].alternative == ""
    assert orig_map["repo_path"].help is not None
    assert orig_map["repo_path"].alternative == ""

    # Ensure no suggestion has both help and alternative set (constructor enforces this)
    for ac in ac_list:
        assert not (ac.help and ac.alternative), f"Suggestion {ac.original} has both help and alternative set"
