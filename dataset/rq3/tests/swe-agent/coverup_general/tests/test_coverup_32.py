# file: sweagent/run/run_single.py:68-117
# asked: {"lines": [92, 93, 96, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 116], "branches": [[95, 96]]}
# gained: {"lines": [92, 93, 96, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 113, 114, 116], "branches": [[95, 96]]}

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_set_default_output_dir_unknown_model_and_path_stem(monkeypatch, tmp_path):
    rs = importlib.import_module("sweagent.run.run_single")
    RunSingleConfig = rs.RunSingleConfig

    # Patch getpass.getuser used in the module to return a predictable user id
    monkeypatch.setattr(rs.getpass, "getuser", lambda: "tester_user")

    # Create a bare instance without invoking pydantic initialization
    inst = object.__new__(RunSingleConfig)

    # Prepare minimal pydantic internals so __setattr__ and __getattr__ won't fail
    object.__setattr__(inst, "__pydantic_fields_set__", set())
    object.__setattr__(inst, "__pydantic_extra__", {})
    object.__setattr__(inst, "__pydantic_private__", {})
    object.__setattr__(inst, "__private_attributes__", {})

    # Now set attributes expected by set_default_output_dir
    setattr(inst, "output_dir", Path("DEFAULT"))
    setattr(inst, "problem_statement", SimpleNamespace(id="problem_42"))
    # Make agent such that accessing .model raises AttributeError -> triggers except branch
    setattr(inst, "agent", SimpleNamespace())  # has no 'model' attribute
    # Set _config_files to a Path so isinstance branch is taken and .stem is used
    setattr(inst, "_config_files", [Path("my_config.toml")])

    # Call method under test
    inst.set_default_output_dir()

    expected = (
        Path.cwd()
        / "trajectories"
        / "tester_user"
        / f"my_config__unknown_model___problem_42"
    )
    assert inst.output_dir == expected


def test_get_auto_correct_returns_expected_suggestions():
    rs = importlib.import_module("sweagent.run.run_single")
    RunSingleConfig = rs.RunSingleConfig
    common_mod = importlib.import_module("sweagent.run.common")
    ACS = common_mod.AutoCorrectSuggestion

    suggestions = RunSingleConfig._get_auto_correct()
    assert isinstance(suggestions, list)
    assert len(suggestions) == 9

    originals = [s.original for s in suggestions]
    for expected_original in [
        "model",
        "agent.model",
        "model.name",
        "per_instance_cost_limit",
        "model.per_instance_cost_limit",
        "config_file",
        "data_path",
        "repo_path",
        "repo.path",
    ]:
        assert expected_original in originals

    data_path_entry = next(s for s in suggestions if s.original == "data_path")
    assert data_path_entry.help is not None
    assert data_path_entry.alternative == ""

    repo_path_entry = next(s for s in suggestions if s.original == "repo_path")
    assert repo_path_entry.help is not None
    assert "no longer" in repo_path_entry.help

    for s in suggestions:
        assert isinstance(s, ACS)
        assert isinstance(s.original, str)
        assert isinstance(s.alternative, str)
