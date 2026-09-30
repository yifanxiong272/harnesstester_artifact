import importlib
import types
from types import SimpleNamespace
import re
import pytest
from pathlib import Path

# Import the module under test
module_path = "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"
mod = importlib.import_module(module_path)

# Helper test doubles and factories
class DummyT:
    def __init__(self, key):
        self.key = key
    def r(self, **kwargs):
        # Return a simple prompt string; include error if provided for determinism
        if "error" in kwargs and kwargs["error"]:
            return f"user prompt with error: {kwargs['error']}"
        return f"prompt-for-{self.key}"

class DummyAPIBackend:
    def __init__(self, response="backend_response"):
        self._response = response
    def build_messages_and_create_chat_completion(self, *, user_prompt, system_prompt):
        # Return always the same value (it will be passed to PythonAgentOut.extract_output)
        return self._response

class DummyPythonAgentOut:
    @staticmethod
    def extract_output(payload):
        # The tests will rely on different generated_code values; payload ignored
        return payload if isinstance(payload, str) else "generated_code"

class DummyResult:
    def __init__(self, exit_code, stdout):
        self.exit_code = exit_code
        self._stdout = stdout
    def get_truncated_stdout(self):
        return self._stdout

class DummyWorkspace:
    def __init__(self, run_results):
        # run_results: list of (exit_code, stdout) tuples. Each call to run pops the next.
        self._run_results = list(run_results)
        # IMPORTANT: use a Path for workspace_path so code using Path(...) / 'file' works
        self.workspace_path = Path("/dummy_ws")
        self.injected_files = {}
        self.experiment_workspace = None
    def inject_code_from_file_dict(self, fd):
        # store for inspection if needed
        self.experiment_workspace = SimpleNamespace(file_dict=fd)
    def inject_files(self, **kwargs):
        self.injected_files.update(kwargs)
    def run(self, *, env, entry):
        if not self._run_results:
            # Default failing run
            return DummyResult(exit_code=1, stdout="failed-run")
        exit_code, stdout = self._run_results.pop(0)
        return DummyResult(exit_code=exit_code, stdout=stdout)


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch):
    # Patch T, APIBackend, PythonAgentOut, FBWorkspace, get_ds_env, DS_RD_SETTING, shutil.copy, and _parsing_score
    monkeypatch.setattr(mod, "T", lambda key: DummyT(key))
    monkeypatch.setattr(mod, "APIBackend", lambda: DummyAPIBackend(response="generated_script_code"))
    monkeypatch.setattr(mod, "PythonAgentOut", DummyPythonAgentOut)

    # By default, DS_RD_SETTING values
    dummy_setting = SimpleNamespace(full_timeout=5, local_data_path="/data/local")
    monkeypatch.setattr(mod, "DS_RD_SETTING", dummy_setting)

    # get_ds_env just returns a dummy env object
    monkeypatch.setattr(mod, "get_ds_env", lambda **kwargs: {"env_called_with": kwargs})

    # Avoid actual filesystem copies
    monkeypatch.setattr(mod.shutil, "copy", lambda *a, **k: None)

    # Ensure shrink_text deterministic (use existing function if present)
    # Provide a simple deterministic shrink_text if not available
    if not hasattr(mod, "shrink_text"):
        monkeypatch.setattr(mod, "shrink_text", lambda s, **k: s)

    yield


def make_reference_exp_with_main(code="print('main')"):
    # minimal stand-in for DSExperiment-like object
    exp_ws = SimpleNamespace(file_dict={"main.py": code})
    return SimpleNamespace(experiment_workspace=exp_ws)


def test_generate_and_run_script_grade_success_round_053(monkeypatch):
    """
    Grade path: script_type != 'data', run returns exit_code 0, and _parsing_score returns a non-None
    value -> should return the generated code.
    """
    # Arrange
    # Force only one retry attempt to simplify flow
    monkeypatch.setattr(mod, "MAX_API_RETRIES", 1)

    # Patch PythonAgentOut.extract_output to return the generated grade script
    monkeypatch.setattr(mod, "PythonAgentOut", DummyPythonAgentOut)
    # Create a workspace that returns a single successful run for the grade script
    ws_factory = lambda: DummyWorkspace(run_results=[(0, "grade stdout with score: 0.95")])
    monkeypatch.setattr(mod, "FBWorkspace", ws_factory)

    # Ensure parsing picks up a score
    monkeypatch.setattr(mod, "_parsing_score", lambda stdout: 0.95)

    reference_exp = make_reference_exp_with_main(code="print('main')")

    # Act
    result = mod.ValidationSelector._generate_and_run_script(
        object(),  # dummy self
        script_type="grade",
        prompt_template_key="some_template",
        reference_exp=reference_exp,
        competition="comp",
        mock_folder="/mock",
        prompt_kwargs={}
    )

    # Assert
    # The DummyAPIBackend response was "generated_script_code" and PythonAgentOut.extract_output returns it
    assert result == "generated_script_code"


def test_generate_and_run_script_data_submission_exists_round_053(monkeypatch):
    """
    Data path: script_type == 'data', first run of data.py returns exit_code 0, second run (reference_code.py)
    also returns 0 and Path.exists reports a submission.csv => generated_code should be returned.
    """
    monkeypatch.setattr(mod, "MAX_API_RETRIES", 1)

    # Create a workspace that returns two successful runs (data.py then reference_code.py)
    ws_factory = lambda: DummyWorkspace(run_results=[(0, "data run ok"), (0, "reference run ok")])
    monkeypatch.setattr(mod, "FBWorkspace", ws_factory)

    # Make PythonAgentOut return a distinct generated code so we can assert it is returned
    monkeypatch.setattr(mod, "PythonAgentOut", DummyPythonAgentOut)
    monkeypatch.setattr(mod, "APIBackend", lambda: DummyAPIBackend(response="generated_data_code"))

    # Ensure Path.exists returns True for the workspace submission path to simulate a produced submission.csv
    orig_Path_exists = mod.Path.exists
    monkeypatch.setattr(mod.Path, "exists", lambda self: True)

    reference_exp = make_reference_exp_with_main(code="print('main')")

    try:
        result = mod.ValidationSelector._generate_and_run_script(
            object(),
            script_type="data",
            prompt_template_key="some_template",
            reference_exp=reference_exp,
            competition="comp",
            mock_folder="/mock",
            prompt_kwargs={}
        )
    finally:
        # Restore Path.exists to avoid side effects in other tests
        monkeypatch.setattr(mod.Path, "exists", orig_Path_exists)

    assert result == "generated_data_code"


def test_generate_and_run_script_failure_raises_round_053(monkeypatch):
    """
    Simulate persistent failures (script run exit_code != 0) and ensure RuntimeError is raised
    after MAX_API_RETRIES attempts.
    """
    # Reduce retries to 1 so the function raises quickly
    monkeypatch.setattr(mod, "MAX_API_RETRIES", 1)

    # FBWorkspace that always fails
    ws_factory = lambda: DummyWorkspace(run_results=[(1, "error output")])
    monkeypatch.setattr(mod, "FBWorkspace", ws_factory)

    # Keep agent output generation deterministic
    monkeypatch.setattr(mod, "PythonAgentOut", DummyPythonAgentOut)
    monkeypatch.setattr(mod, "APIBackend", lambda: DummyAPIBackend(response="generated_fail_code"))

    reference_exp = make_reference_exp_with_main(code="print('main')")

    with pytest.raises(RuntimeError):
        mod.ValidationSelector._generate_and_run_script(
            object(),
            script_type="grade",
            prompt_template_key="some_template",
            reference_exp=reference_exp,
            competition="comp",
            mock_folder="/mock",
            prompt_kwargs={}
        )
