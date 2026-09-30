# file: rdagent/scenarios/data_science/proposal/exp_gen/select/submit.py:429-513
# asked: {"lines": [439, 440, 442, 443, 444, 446, 447, 448, 453, 454, 455, 456, 457, 459, 461, 462, 463, 464, 469, 470, 471, 473, 474, 477, 478, 480, 482, 483, 484, 485, 486, 489, 490, 491, 493, 494, 495, 496, 498, 500, 502, 504, 505, 506, 508, 510, 512, 513], "branches": [[443, 444], [443, 513], [459, 461], [459, 469], [482, 483], [482, 510], [484, 485], [484, 504], [491, 493], [491, 502], [493, 494], [493, 500], [505, 506], [505, 508]]}
# gained: {"lines": [439, 440, 442, 443, 444, 446, 447, 448, 453, 454, 455, 456, 457, 459, 461, 462, 463, 464, 469, 470, 471, 473, 474, 477, 478, 480, 482, 483, 484, 485, 486, 489, 490, 491, 493, 494, 495, 496, 498, 504, 505, 506, 510, 512, 513], "branches": [[443, 444], [443, 513], [459, 461], [459, 469], [482, 483], [482, 510], [484, 485], [484, 504], [491, 493], [493, 494], [505, 506]]}

import io
import shutil
from types import SimpleNamespace
from pathlib import Path
import pytest
import importlib

MODULE_PATH = "rdagent.scenarios.data_science.proposal.exp_gen.select.submit"


@pytest.fixture
def submit_mod(monkeypatch, tmp_path):
    mod = importlib.import_module(MODULE_PATH)

    # Provide a controllable T that returns predictable prompts
    class DummyT:
        def __init__(self, key):
            self.key = key

        def r(self, *args, **kwargs):
            # Return distinct values for system vs user prompts for clarity
            if "sample_data.system" in self.key:
                return "SYSTEM_PROMPT"
            return f"USER_PROMPT:{self.key}"

    monkeypatch.setattr(mod, "T", DummyT)

    # Patch APIBackend to a dummy builder; content is ignored because we patch extract_output
    class DummyAPIBackend:
        def build_messages_and_create_chat_completion(self, *args, **kwargs):
            return {"dummy": "result"}

    monkeypatch.setattr(mod, "APIBackend", DummyAPIBackend)

    # DS_RD_SETTING required attributes
    monkeypatch.setattr(mod, "DS_RD_SETTING", SimpleNamespace(local_data_path=str(tmp_path / "localdata"), full_timeout=5))

    # Generic get_ds_env that accepts kwargs and returns a dummy env object
    def dummy_get_ds_env(*args, **kwargs):
        return SimpleNamespace(env_description="env", kwargs=kwargs)

    monkeypatch.setattr(mod, "get_ds_env", dummy_get_ds_env)

    return mod


def make_fake_reference_exp(tmp_path, *, main_py_content="print('main')\n"):
    # Minimal fake DSExperiment with experiment_workspace.file_dict
    fake_ws = SimpleNamespace(file_dict={"main.py": main_py_content})
    fake_exp = SimpleNamespace(experiment_workspace=fake_ws)
    return fake_exp


class FakeWorkspace:
    def __init__(self, workspace_path: Path):
        self.workspace_path = Path(workspace_path)
        self.file_dict = {}
        self._injected_files = {}
        # ensure workspace directory exists so shutil.copy destinations work
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def inject_code_from_file_dict(self, file_dict):
        # Accept either an object with attribute file_dict or a plain dict
        if hasattr(file_dict, "file_dict"):
            fd = file_dict.file_dict
        else:
            fd = file_dict
        if isinstance(fd, dict):
            self.file_dict.update(fd)
        else:
            raise TypeError("inject_code_from_file_dict expects a dict-like file_dict")

    def inject_files(self, **files):
        # write files into the workspace path so any scripts that inspect files can see them
        for name, content in files.items():
            self._injected_files[name] = content
            path = self.workspace_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            # ensure content is a string
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(str(content))

    def run(self, env, entry):
        """
        Simulate running different scripts based on entry.
        For our tests:
        - If 'reference_code.py' in entry: create submission.csv to simulate success.
        - If 'data.py' in entry: return exit_code=0 to indicate success.
        - If 'grade.py' in entry: return exit_code=0 with a score line.
        """
        class Result:
            def __init__(self, exit_code, stdout):
                self.exit_code = exit_code
                self._stdout = stdout

            def get_truncated_stdout(self):
                return self._stdout

        ent = entry or ""
        if "data.py" in ent:
            return Result(0, "Generated data successfully")
        if "reference_code.py" in ent:
            # write a submission.csv into workspace to simulate reference run producing it
            (self.workspace_path / "submission.csv").write_text("id,score\n1,0.5\n")
            return Result(0, "reference executed")
        if "grade.py" in ent:
            return Result(0, "SCORE: 0.77\n")
        return Result(1, "error occurred")


@pytest.mark.usefixtures("submit_mod")
def test_generate_and_run_script_data_success(submit_mod, monkeypatch, tmp_path):
    mod = submit_mod

    # Prepare generated code to be returned by the agent extractor
    generated_code = "# generated data code\nprint('data')\n"

    # Patch PythonAgentOut.extract_output to return our generated_code
    monkeypatch.setattr(mod.PythonAgentOut, "extract_output", staticmethod(lambda x: generated_code))

    # Patch FBWorkspace to our FakeWorkspace bound to a tmp workspace dir
    def fake_ws_factory():
        ws_dir = tmp_path / "ws_data"
        return FakeWorkspace(ws_dir)

    monkeypatch.setattr(mod, "FBWorkspace", fake_ws_factory)

    # Ensure _parsing_score default behavior doesn't interfere
    monkeypatch.setattr(mod, "_parsing_score", lambda s: None)

    # Create a reference experiment with main.py content (reference_code)
    reference_exp = make_fake_reference_exp(tmp_path, main_py_content="print('main logic')\n")

    # Prepare mock_folder where final submission.csv will be copied to
    mock_folder = tmp_path / "mock"
    mock_folder.mkdir()

    # Now run the method under test: script_type "data"
    sel = mod.ValidationSelector(candidate=[], direction_sign=1, competition="comp", only_sample=False, sample_code_path=str(tmp_path))
    code = sel._generate_and_run_script(
        script_type="data",
        prompt_template_key="sample_data",
        reference_exp=reference_exp,
        competition="comp",
        mock_folder=str(mock_folder),
        prompt_kwargs={},
    )

    # Assertions: returned code equals generated_code
    assert code == generated_code

    # After running, submission.csv should exist in mock_folder (copied by code)
    assert (mock_folder / "submission.csv").exists()
    content = (mock_folder / "submission.csv").read_text()
    assert "id,score" in content


def test_generate_and_run_script_grade_score_success(submit_mod, monkeypatch, tmp_path):
    mod = submit_mod

    generated_code = "# grade script\nprint('grade')\n"
    monkeypatch.setattr(mod.PythonAgentOut, "extract_output", staticmethod(lambda x: generated_code))

    # Create a workspace factory - grade will copy submission.csv from mock folder into ws before running
    def fake_ws_factory():
        ws_dir = tmp_path / "ws_grade"
        return FakeWorkspace(ws_dir)

    monkeypatch.setattr(mod, "FBWorkspace", fake_ws_factory)

    # Ensure that parsing score returns a numeric when called (simulate parsing of stdout)
    monkeypatch.setattr(mod, "_parsing_score", lambda stdout: 0.77 if "SCORE" in stdout.upper() else None)

    # Create mock_folder with a submission.csv so grade.py can be run (code copies this into workspace before running)
    mock_folder = tmp_path / "mock_grade"
    mock_folder.mkdir()
    (mock_folder / "submission.csv").write_text("id,score\n1,0.5\n")

    reference_exp = make_fake_reference_exp(tmp_path, main_py_content="print('main logic')\n")

    sel = mod.ValidationSelector(candidate=[], direction_sign=1, competition="comp", only_sample=False, sample_code_path=str(tmp_path))

    code = sel._generate_and_run_script(
        script_type="grade",
        prompt_template_key="sample_grade",
        reference_exp=reference_exp,
        competition="comp",
        mock_folder=str(mock_folder),
        prompt_kwargs={},
    )

    assert code == generated_code


def test_generate_and_run_script_fails_after_retries(submit_mod, monkeypatch, tmp_path):
    mod = submit_mod

    # Always return some generated code but workspace runs always fail and parsing returns None
    monkeypatch.setattr(mod.PythonAgentOut, "extract_output", staticmethod(lambda x: "# bad code\n"))

    # Fake workspace that always returns failure (non-zero and no parseable score)
    class AlwaysFailWS(FakeWorkspace):
        def run(self, env, entry):
            class Result:
                def __init__(self):
                    self.exit_code = 1

                def get_truncated_stdout(self):
                    return "no score here"
            return Result()

    def fake_ws_factory():
        return AlwaysFailWS(tmp_path / "ws_fail")

    monkeypatch.setattr(mod, "FBWorkspace", fake_ws_factory)

    # Force MAX_API_RETRIES to small number to speed test
    monkeypatch.setattr(mod, "MAX_API_RETRIES", 2)

    # Ensure parsing returns None so no success path possible
    monkeypatch.setattr(mod, "_parsing_score", lambda s: None)

    reference_exp = make_fake_reference_exp(tmp_path, main_py_content="print('main logic')\n")
    mock_folder = tmp_path / "mock_fail"
    mock_folder.mkdir()
    # Create submission.csv so the code proceeds to copy it into the workspace before running and failing
    (mock_folder / "submission.csv").write_text("id,score\n1,0.5\n")

    sel = mod.ValidationSelector(candidate=[], direction_sign=1, competition="comp", only_sample=False, sample_code_path=str(tmp_path))

    with pytest.raises(RuntimeError) as excinfo:
        sel._generate_and_run_script(
            script_type="grade",
            prompt_template_key="sample_grade",
            reference_exp=reference_exp,
            competition="comp",
            mock_folder=str(mock_folder),
            prompt_kwargs={},
        )

    assert "Failed to generate a working grade.py" in str(excinfo.value)
