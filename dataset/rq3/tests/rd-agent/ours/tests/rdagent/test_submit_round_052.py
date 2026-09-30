import shutil
import time
from pathlib import Path
from types import SimpleNamespace
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen.select import submit as submit_mod

# Dummy helpers to patch into the module under test
class DummyT:
    def __init__(self, *a, **k):
        pass

    def r(self):
        # consistent input folder used by the code under test
        return "workspace_input"

class DummyFBWorkspace:
    def __init__(self):
        self._injected_files = {}
        self._injected_code = None

    def inject_code_from_file_dict(self, fd):
        # store supplied dict for inspection if needed
        self._injected_code = fd

    def inject_files(self, **kwargs):
        self._injected_files.update(kwargs)

    def run(self, env, entry):
        # return object with exit_code attribute as used by the function
        return SimpleNamespace(exit_code=0)


@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    # Patch T to return a deterministic input folder name
    monkeypatch.setattr(submit_mod, "T", DummyT)
    # Patch FBWorkspace to avoid real workspace/runtime operations
    monkeypatch.setattr(submit_mod, "FBWorkspace", DummyFBWorkspace)
    # Patch get_ds_env to avoid docker/runner side effects
    monkeypatch.setattr(submit_mod, "get_ds_env", lambda **kwargs: {"_dummy_env": True})
    # Ensure DS_RD_SETTING has the attribute used in the code
    class DummySetting:
        local_data_path = "./local_data_path"
        full_timeout = 123

    monkeypatch.setattr(submit_mod, "DS_RD_SETTING", DummySetting)
    yield


def make_selector_instance():
    # Create a ValidationSelector instance without invoking its real __init__
    # and set only the attributes needed by _prepare_validation_scripts.
    SelectorCls = submit_mod.ValidationSelector
    selector = object.__new__(SelectorCls)
    # sample_code_path and sample_rate are used by the function
    selector.sample_code_path = Path(".")
    selector.sample_rate = 0.8

    # Provide a simple print_code to capture calls (no-op)
    selector._printed = []

    def print_code(data, grade):
        selector._printed.append((data, grade))

    selector.print_code = print_code
    return selector


def test_missing_reference_code_round_052(tmp_path):
    """When reference experiment has no main.py or empty main.py -> RuntimeError"""
    selector = make_selector_instance()
    # reference_exp with empty or missing main.py
    reference_exp = SimpleNamespace(experiment_workspace=SimpleNamespace(file_dict={}))

    with pytest.raises(RuntimeError, match="No code found in the reference experiment"):
        selector._prepare_validation_scripts(reference_exp, "comp", str(tmp_path / "mock"))


def test_sample_exists_no_label_and_ws_run_success_round_052(tmp_path):
    """When sample data.py & grade.py exist and label missing, workspace run called and sample_rate replacement applied"""
    selector = make_selector_instance()

    # Create a sample_code_path structure with competition/data.py and grade.py
    sample_dir = tmp_path / "samples"
    comp = "mycomp"
    data_src = sample_dir / comp
    data_src.mkdir(parents=True)
    data_py = data_src / "data.py"
    grade_py = data_src / "grade.py"
    # Include markers 0.8 and 0.2 so replacement can be observed
    data_py.write_text("# sample data script\nSPLIT = 0.8\nOTHER = 0.2\n")
    grade_py.write_text("# sample grade script\nprint('grade')\n")

    selector.sample_code_path = sample_dir
    selector.sample_rate = 0.5  # trigger replacement of 0.8 -> 0.5 and 0.2 -> 0.5

    # Prepare mock folder where data.py / grade.py will be copied to
    mock_folder = tmp_path / "mock_folder"
    mock_folder.mkdir()

    # Confirm label does NOT exist so branch creating FBWorkspace and run() executes
    label_path = mock_folder / "workspace_input" / "label.csv"
    assert not label_path.exists()

    # Call the target function
    reference_exp = SimpleNamespace(experiment_workspace=SimpleNamespace(file_dict={"main.py": "print(1)"}))

    data_code, grade_code = selector._prepare_validation_scripts(reference_exp, comp, str(mock_folder))

    # Assert replacements happened in the returned data code
    assert "0.5" in data_code
    # Grade code should be read from copied file (unchanged content)
    assert "grade script" in grade_code
    # print_code should have been invoked once because DummyFBWorkspace.run() returns exit_code 0
    assert len(selector._printed) >= 1


def test_generate_data_and_grade_round_052(tmp_path):
    """When data.py/grade.py missing, generator is invoked for both data and grade scripts and files are written"""
    selector = make_selector_instance()

    # Use a mock_folder with no data.py / grade.py
    mock_folder = tmp_path / "mock2"
    mock_folder.mkdir()

    # Provide a reference_exp with a non-empty main.py so the function proceeds
    reference_exp = SimpleNamespace(experiment_workspace=SimpleNamespace(file_dict={"main.py": "print('x')"}))

    # Patch the instance method _generate_and_run_script to return deterministic outputs
    def fake_generate_and_run_script(script_type, prompt_template_key, reference_exp, competition, mock_folder, prompt_kwargs):
        if script_type == "data":
            return "# GENERATED DATA SCRIPT\nprint('DATA')\n"
        elif script_type == "grade":
            return "# GENERATED GRADE SCRIPT\nprint('GRADE')\n"
        else:
            return ""

    selector._generate_and_run_script = fake_generate_and_run_script

    # Ensure no data.py exists initially in mock_folder
    data_path = Path(mock_folder) / "data.py"
    grade_path = Path(mock_folder) / "grade.py"
    if data_path.exists():
        data_path.unlink()
    if grade_path.exists():
        grade_path.unlink()

    data_code, grade_code = selector._prepare_validation_scripts(reference_exp, "comp", str(mock_folder))

    # After generation the returned texts should match our fake generator outputs
    assert "GENERATED DATA SCRIPT" in data_code
    assert "GENERATED GRADE SCRIPT" in grade_code

    # Files should have been written to disk
    assert data_path.exists()
    assert grade_path.exists()

    # print_code should have been invoked when grade was generated
    assert len(selector._printed) >= 1
