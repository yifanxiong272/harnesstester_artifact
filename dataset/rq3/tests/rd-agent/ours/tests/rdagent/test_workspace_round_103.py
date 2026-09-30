import importlib
import types
from pathlib import Path
import pandas as pd
import pytest


def _make_dummy_env(match_output=None):
    class DummyEnv:
        def __init__(self, conf=None):
            self.conf = conf
            self.prepared = False

        def prepare(self):
            self.prepared = True

        def check_output(self, local_path: str, entry: str, env: dict):
            # Return different outputs based on the entry to mirror the real behavior
            if entry.startswith("qrun"):
                # Provide strings that match the regex pattern used in the SUT
                return (
                    "Epoch1: train -0.123, valid -0.234\n"
                    "best score: -0.111 @ 3 epoch\n"
                    "unrelated line"
                )
            return "read-exp-done"

    return DummyEnv


class DummyLogger:
    def __init__(self):
        self.logged = []
        self.errors = []

    def log_object(self, obj, tag=None):
        # store shallow info for assertions
        self.logged.append((tag, obj))

    def error(self, msg):
        self.errors.append(msg)


def _patch_core_workspace(monkeypatch, tmp_path, env_type, env_cls=None):
    """Patch the minimal external contracts used by QlibFBWorkspace so tests are deterministic.

    This patches:
    - rdagent.core.experiment.FBWorkspace.__init__ to set a workspace_path at tmp_path
    - rdagent.core.experiment.FBWorkspace.inject_code_from_folder to be a no-op that records a value
    - MODEL_COSTEER_SETTINGS on the workspace module to control env_type
    - QTDockerEnv/QlibCondaEnv/QlibCondaConf on the workspace module to deterministic fakes
    - logger on the workspace module to a DummyLogger

    Returns (workspace_module, dummy_logger)
    """
    # Import the modules under test
    import rdagent.core.experiment as core_exp
    import rdagent.scenarios.qlib.experiment.workspace as workspace

    # Patch FBWorkspace.__init__ to avoid dependency on the real base class init
    def _fb_init(self, *a, **kw):
        # ensure the instance has a workspace_path attribute expected by the SUT
        self.workspace_path = tmp_path

    monkeypatch.setattr(core_exp.FBWorkspace, "__init__", _fb_init, raising=False)
    # Provide a simple inject_code_from_folder to satisfy QlibFBWorkspace.__init__'s call
    monkeypatch.setattr(
        core_exp.FBWorkspace,
        "inject_code_from_folder",
        lambda self, p: setattr(self, "_injected_code_path", str(p)),
        raising=False,
    )

    # Replace MODEL_COSTEER_SETTINGS in the workspace module
    monkeypatch.setattr(
        workspace,
        "MODEL_COSTEER_SETTINGS",
        types.SimpleNamespace(env_type=env_type),
        raising=False,
    )

    # Provide deterministic environment classes
    if env_cls is None:
        env_cls = _make_dummy_env()

    monkeypatch.setattr(workspace, "QTDockerEnv", env_cls, raising=False)
    # QlibCondaEnv gets constructed with conf=QlibCondaConf(); we provide a dummy conf factory
    monkeypatch.setattr(workspace, "QlibCondaEnv", env_cls, raising=False)
    monkeypatch.setattr(workspace, "QlibCondaConf", lambda: None, raising=False)

    # Patch logger to capture messages
    dummy_logger = DummyLogger()
    monkeypatch.setattr(workspace, "logger", dummy_logger, raising=False)

    return workspace, dummy_logger


def test_docker_success_round_103(monkeypatch, tmp_path):
    """Docker env: both ret.pkl and qlib_res.csv exist -> returns series and filtered execute_qlib_log

    Covers: env_type == 'docker', ret.pkl exists branch, qlib_res.csv exists branch, regex extraction
    """
    # Prepare environment and patches
    workspace, logger = _patch_core_workspace(monkeypatch, tmp_path, env_type="docker")

    # Create a deterministic ret.pkl (pickled DataFrame) and qlib_res.csv on workspace path
    df_ret = pd.DataFrame({"retcol": [0.1, 0.2]}, index=["a", "b"])
    ret_path = tmp_path / "ret.pkl"
    df_ret.to_pickle(ret_path)

    df_res = pd.DataFrame({"metric": [42, 43]}, index=["r1", "r2"])
    qlib_res_path = tmp_path / "qlib_res.csv"
    df_res.to_csv(qlib_res_path)

    # Ensure the fake env returns predictable execute_qlib_log
    env_cls = _make_dummy_env()
    monkeypatch.setattr(workspace, "QTDockerEnv", env_cls, raising=False)

    # Instantiate and run
    w = workspace.QlibFBWorkspace(template_folder_path=Path("/template"))
    series, exec_log = w.execute(qlib_config_name="conf.yaml", run_env={})

    # Assert returned series equals the first column of the CSV (index preserved)
    expected_series = pd.read_csv(qlib_res_path, index_col=0).iloc[:, 0]
    # Use equals for deterministic comparison
    assert series.equals(expected_series)

    # The regex in the SUT should extract the matching lines; ensure exec_log equals the joined matches
    assert "Epoch1: train -0.123" in exec_log
    assert "best score: -0.111 @ 3 epoch" in exec_log

    # Logger should have recorded the Qlib execute log and the quantitative backtesting chart
    tags = [t for t, _ in logger.logged]
    assert "Qlib_execute_log" in tags
    assert "Quantitative Backtesting Chart" in tags


def test_conda_no_ret_round_103(monkeypatch, tmp_path):
    """Conda env: ret.pkl missing -> logs error and returns (None, execute_qlib_log)

    Covers: env_type == 'conda' branch, missing ret.pkl branch (No result file)
    """
    workspace, logger = _patch_core_workspace(monkeypatch, tmp_path, env_type="conda")

    # Ensure no ret.pkl exists
    assert not (tmp_path / "ret.pkl").exists()

    # Provide conda env implementation
    monkeypatch.setattr(workspace, "QlibCondaEnv", _make_dummy_env(), raising=False)

    w = workspace.QlibFBWorkspace(template_folder_path=Path("/template"))
    result = w.execute(qlib_config_name="conf.yaml", run_env={})

    # Expect early return because ret.pkl does not exist
    assert result[0] is None
    # The second element should be the raw execute_qlib_log returned by the env fake
    assert isinstance(result[1], str)

    # The logger should have recorded the error about missing result file
    assert any("No result file found." in e for e in logger.errors)


def test_docker_no_qlib_res_round_103(monkeypatch, tmp_path):
    """Docker env: ret.pkl exists but qlib_res.csv missing -> logs file-missing error and returns (None, execute_qlib_log)

    Covers: qlib_res.csv missing branch
    """
    workspace, logger = _patch_core_workspace(monkeypatch, tmp_path, env_type="docker")

    # Create only ret.pkl
    df_ret = pd.DataFrame({"retcol": [0.1]}, index=["a"])
    (tmp_path / "ret.pkl").to_pickle = df_ret.to_pickle  # ensure attribute exists
    df_ret.to_pickle(tmp_path / "ret.pkl")

    # Ensure qlib_res.csv is absent
    assert not (tmp_path / "qlib_res.csv").exists()

    # Fake environment
    monkeypatch.setattr(workspace, "QTDockerEnv", _make_dummy_env(), raising=False)

    w = workspace.QlibFBWorkspace(template_folder_path=Path("/template"))
    result = w.execute(qlib_config_name="conf.yaml", run_env={})

    assert result[0] is None
    assert isinstance(result[1], str)
    # The logger should contain the file-does-not-exist message
    assert any("does not exist" in e for e in logger.errors)


def test_unknown_env_round_103(monkeypatch, tmp_path):
    """Unknown env type -> logs unknown env and returns (None, 'Unknown environment type')

    Covers: default/else branch when MODEL_COSTEER_SETTINGS.env_type is unrecognized
    """
    workspace, logger = _patch_core_workspace(monkeypatch, tmp_path, env_type="kubernetes")

    w = workspace.QlibFBWorkspace(template_folder_path=Path("/template"))
    res = w.execute(qlib_config_name="conf.yaml", run_env={})

    # The code returns (None, "Unknown environment type") in this branch
    assert res == (None, "Unknown environment type")
    # Ensure logger recorded the unknown env error containing the env type
    assert any("Unknown env_type" in e or "Unknown env_type" in str(e) or "kubernetes" in str(e) for e in logger.errors)
