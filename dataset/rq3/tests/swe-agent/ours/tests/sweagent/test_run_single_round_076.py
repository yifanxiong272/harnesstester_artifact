import types
from pathlib import Path

import pytest

import sweagent.run.run_single as rs


def _make_minimal_instance():
    # Avoid pydantic validation by constructing the object without __init__
    obj = object.__new__(rs.RunSingleConfig)
    return obj


def test_set_default_output_dir_path_config_round_076(monkeypatch):
    """
    - Patch getpass.getuser and Path.cwd to deterministic values.
    - Provide _config_files with a Path instance to hit the branch that calls .stem
    - Ensure agent has no .model attribute so attribute access raises AttributeError
      and the fallback model_id == "unknown_model" branch is executed.
    """
    # Deterministic environment
    monkeypatch.setattr(rs.getpass, "getuser", lambda: "fixeduser")
    monkeypatch.setattr(rs.Path, "cwd", lambda: Path("/fixedcwd"))

    cfg = _make_minimal_instance()
    cfg.output_dir = Path("DEFAULT")

    # problem_statement with an id attribute
    cfg.problem_statement = types.SimpleNamespace(id="prob-id-1")

    # agent without a .model attribute => AttributeError on access
    cfg.agent = types.SimpleNamespace()  # no 'model' attribute

    # first config file is a Path -> triggers config_file.stem branch
    cfg._config_files = [Path("my_conf.yml")]

    cfg.set_default_output_dir()

    expected = Path("/fixedcwd") / "trajectories" / "fixeduser" / "my_conf__unknown_model___prob-id-1"
    assert cfg.output_dir == expected


def test_set_default_output_dir_str_config_round_076(monkeypatch):
    """
    - Ensure when the first _config_files item is a plain string, the code keeps it
      and does not call .stem (other branch from Path case).
    - Also exercise the AttributeError fallback for agent.model.id again.
    """
    monkeypatch.setattr(rs.getpass, "getuser", lambda: "anotheruser")
    monkeypatch.setattr(rs.Path, "cwd", lambda: Path("/anothercwd"))

    cfg = _make_minimal_instance()
    cfg.output_dir = Path("DEFAULT")
    cfg.problem_statement = types.SimpleNamespace(id="prob-2")
    cfg.agent = types.SimpleNamespace()  # no 'model' attribute

    # first config file is a string -> should be used verbatim in the output dir
    cfg._config_files = ["cfg_string"]

    cfg.set_default_output_dir()

    expected = Path("/anothercwd") / "trajectories" / "anotheruser" / "cfg_string__unknown_model___prob-2"
    assert cfg.output_dir == expected


def test__get_auto_correct_round_076(monkeypatch):
    """
    - Patch the ACS symbol inside the module to a lightweight recorder class
      so construction of the list of suggestions is deterministic and cheap.
    - Verify that the returned list is built from ACS calls with expected args
      (this covers the _get_auto_correct return construction).
    """

    class DummyACS:
        def __init__(self, *args, **kwargs):
            # record positional and keyword args for assertions
            self.args = args
            self.kwargs = kwargs

        def __repr__(self):
            return f"DummyACS{self.args}{self.kwargs}"

    monkeypatch.setattr(rs, "ACS", DummyACS)

    suggestions = rs.RunSingleConfig._get_auto_correct()

    assert isinstance(suggestions, list)
    # there should be multiple suggestions as per the original list
    assert len(suggestions) >= 3

    # First few suggestions are expected to have specific positional args
    assert suggestions[0].args[0] == "model"
    assert suggestions[0].args[1] == "agent.model.name"

    assert suggestions[1].args[0] == "agent.model"
    assert suggestions[1].args[1] == "agent.model.name"

    # One of the suggestions uses a 'help' keyword argument; ensure kwargs preserved
    has_help = any((s.kwargs.get("help") is not None) for s in suggestions)
    assert has_help
