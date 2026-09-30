import importlib
import traceback
from types import SimpleNamespace
from pathlib import Path

import pytest

# Import the module under test and utils to patch RD_AGENT_SETTINGS
model = importlib.import_module("rdagent.components.coder.model_coder.model")
import rdagent.core.utils as utils

class DummyTask:
    def __init__(self, version, model_type="dummy"):
        self.version = version
        self.model_type = model_type

class DummySelf:
    def __init__(self, target_task, workspace_path="/tmp/workspace"):
        self._before_called = False
        self.target_task = target_task
        self.workspace_path = workspace_path

    def before_execute(self):
        # simple side-effect to verify it was called
        self._before_called = True


def _patch_templates(monkeypatch, v1_text="V1_TEMPLATE_CONTENT", v2_text="V2_TEMPLATE_CONTENT"):
    # Patch the Path.read_text used inside the module so v1/v2 templates return known contents
    def fake_read_text(self, *args, **kwargs):
        # self is a pathlib.Path instance; choose by filename
        s = str(self)
        if s.endswith("model_execute_template_v1.txt"):
            return v1_text
        if s.endswith("model_execute_template_v2.txt"):
            return v2_text
        return ""

    monkeypatch.setattr(model.Path, "read_text", fake_read_text, raising=False)


def test_docker_success_round_082(monkeypatch):
    """
    - target_task.version == 1
    - MODEL_COSTEER_SETTINGS.env_type == "docker"
    - QTDockerEnv.prepare called and dump returns results
    - verify returned values match the results
    """
    # Disable caching to avoid invoking hash_func which expects workspace attributes
    monkeypatch.setattr(utils.RD_AGENT_SETTINGS, "cache_with_pickle", False, raising=False)

    dummy_self = DummySelf(DummyTask(version=1, model_type="mtype"))
    _patch_templates(monkeypatch, v1_text="LINE_FROM_V1_TEMPLATE")

    # Fake settings
    monkeypatch.setattr(model, "MODEL_COSTEER_SETTINGS", SimpleNamespace(env_type="docker"))

    # Fake QTDockerEnv
    class FakeQT:
        def __init__(self):
            self.prepared = False
            self.last_code = None

        def prepare(self):
            self.prepared = True

        def dump_python_code_run_and_get_results(
            self, code, dump_file_names, local_path, env, code_dump_file_py_name
        ):
            # record code and return a successful result
            self.last_code = code
            return ("LOG_OK", ["FEEDBACK_OK", {"value": 123}])

    monkeypatch.setattr(model, "QTDockerEnv", FakeQT)

    # Run execute
    feedback, output = model.ModelFBWorkspace.execute(dummy_self, batch_size=2, num_features=3, num_timesteps=4, num_edges=5, input_value=0.1, param_init_value=0.2)

    # Assertions
    assert dummy_self._before_called is True
    assert feedback == "FEEDBACK_OK"
    assert output == {"value": 123}

    # Also ensure the generated code contains some formatted values
    inst = FakeQT()
    monkeypatch.setattr(model, "QTDockerEnv", lambda: inst)
    _patch_templates(monkeypatch, v1_text="TEMPLATE_CONTENT")
    fb2, out2 = model.ModelFBWorkspace.execute(dummy_self, batch_size=7, num_features=11, num_timesteps=13, num_edges=17, input_value=1.5, param_init_value=2.5)
    # ensure our instrumented instance recorded code with substituted numeric values
    assert "BATCH_SIZE = 7" in inst.last_code or "BATCH_SIZE = 7" in str(inst.last_code)


def test_conda_success_round_082(monkeypatch):
    """
    - target_task.version == 1
    - MODEL_COSTEER_SETTINGS.env_type == "conda"
    - QlibCondaEnv(conf=QlibCondaConf()) path
    """
    monkeypatch.setattr(utils.RD_AGENT_SETTINGS, "cache_with_pickle", False, raising=False)

    dummy_self = DummySelf(DummyTask(version=1))
    _patch_templates(monkeypatch, v1_text="V1_CONTENT_CONDA")

    monkeypatch.setattr(model, "MODEL_COSTEER_SETTINGS", SimpleNamespace(env_type="conda"))

    # Provide a fake QlibCondaConf and QlibCondaEnv that accept conf kwarg
    class FakeConf:
        def __init__(self):
            self.cfg = "ok"

    class FakeCondaEnv:
        def __init__(self, conf=None):
            self.conf = conf
            self.did_prepare = False
            self.code_seen = None

        def prepare(self):
            self.did_prepare = True

        def dump_python_code_run_and_get_results(self, code, dump_file_names, local_path, env, code_dump_file_py_name):
            self.code_seen = code
            return ("LOG", ["COND_FEED", [1, 2, 3]])

    monkeypatch.setattr(model, "QlibCondaConf", FakeConf)
    monkeypatch.setattr(model, "QlibCondaEnv", FakeCondaEnv)

    feedback, output = model.ModelFBWorkspace.execute(dummy_self)
    assert feedback == "COND_FEED"
    assert output == [1, 2, 3]


def test_unknown_env_type_errors_round_082(monkeypatch):
    """
    - target_task.version == 1
    - MODEL_COSTEER_SETTINGS.env_type is unknown -> ValueError raised inside try
    - exception is caught and returned execution_model_output is None
    """
    monkeypatch.setattr(utils.RD_AGENT_SETTINGS, "cache_with_pickle", False, raising=False)

    dummy_self = DummySelf(DummyTask(version=1))
    _patch_templates(monkeypatch)

    monkeypatch.setattr(model, "MODEL_COSTEER_SETTINGS", SimpleNamespace(env_type="this_is_not_known"))

    feedback, output = model.ModelFBWorkspace.execute(dummy_self)
    # Should not raise, and should contain the unknown env_type string
    assert output is None
    assert "Unknown env_type" in feedback
    assert "this_is_not_known" in feedback


def test_dump_raises_long_error_truncation_round_082(monkeypatch):
    """
    - target_task.version == 1, env_type docker
    - QTDockerEnv.dump_python_code_run_and_get_results raises an Exception with a very long message
    - The resulting execution_feedback_str should be truncated and contain the hidden marker
    """
    monkeypatch.setattr(utils.RD_AGENT_SETTINGS, "cache_with_pickle", False, raising=False)

    dummy_self = DummySelf(DummyTask(version=1))
    _patch_templates(monkeypatch)

    monkeypatch.setattr(model, "MODEL_COSTEER_SETTINGS", SimpleNamespace(env_type="docker"))

    class BadQT:
        def prepare(self):
            pass

        def dump_python_code_run_and_get_results(self, *args, **kwargs):
            # Raise an exception with a very long message to trigger truncation
            long_msg = "X" * 5000
            raise RuntimeError(long_msg)

    monkeypatch.setattr(model, "QTDockerEnv", BadQT)

    feedback, output = model.ModelFBWorkspace.execute(dummy_self)
    assert output is None
    # Must contain the truncation marker from the implementation
    assert "....hidden long error message...." in feedback
    # Ensure the feedback got shortened compared to the original long exception
    assert len(feedback) < 5000


def test_version2_kg_round_082(monkeypatch):
    """
    - target_task.version != 1 (e.g., 2) -> KGDockerEnv path used
    - ensure dump_python_code_run_and_get_results is invoked and its results returned
    """
    monkeypatch.setattr(utils.RD_AGENT_SETTINGS, "cache_with_pickle", False, raising=False)

    dummy_self = DummySelf(DummyTask(version=2))
    _patch_templates(monkeypatch, v2_text="V2_SPECIAL_TEMPLATE")

    monkeypatch.setattr(model, "MODEL_COSTEER_SETTINGS", SimpleNamespace(env_type="ignored_for_v2"))

    class FakeKG:
        def __init__(self):
            self.prepared = False
            self.code = None

        def prepare(self):
            self.prepared = True

        def dump_python_code_run_and_get_results(self, code, dump_file_names, local_path, env, code_dump_file_py_name):
            self.code = code
            return ("KGLOG", ["KG_FEED", {"ok": True}])

    monkeypatch.setattr(model, "KGDockerEnv", FakeKG)

    feedback, output = model.ModelFBWorkspace.execute(dummy_self)
    assert feedback == "KG_FEED"
    assert output == {"ok": True}
