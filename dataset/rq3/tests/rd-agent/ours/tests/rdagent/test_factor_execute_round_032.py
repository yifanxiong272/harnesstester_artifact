import builtins
import subprocess
import uuid
from types import SimpleNamespace
from pathlib import Path
import pandas as pd
import pytest

import rdagent.components.coder.factor_coder.factor as factor_mod
from rdagent.core.exception import CodeFormatError, CustomRuntimeError, NoOutputError


def make_instance(tmp_path, *, file_dict=None, version=1, raise_exception=False):
    # Bypass __init__ to avoid FBWorkspace complex initialization
    inst = object.__new__(factor_mod.FactorFBWorkspace)
    inst.before_execute = lambda: None
    inst.file_dict = file_dict
    inst.workspace_path = tmp_path
    inst.target_task = SimpleNamespace(version=version)
    inst.link_all_files_in_folder_to_workspace = lambda src, dst: None
    inst.raise_exception = raise_exception
    return inst


def test_missing_code_return_round_032(tmp_path):
    inst = make_instance(tmp_path, file_dict=None, raise_exception=False)
    # Call underlying function to avoid cache wrapper side-effects
    feedback, df = factor_mod.FactorFBWorkspace.execute.__wrapped__(inst, "Debug")
    assert feedback == factor_mod.FactorFBWorkspace.FB_CODE_NOT_SET
    assert df is None


def test_missing_code_raise_round_032(tmp_path):
    inst = make_instance(tmp_path, file_dict=None, raise_exception=True)
    with pytest.raises(CodeFormatError):
        factor_mod.FactorFBWorkspace.execute.__wrapped__(inst, "Debug")


def test_version1_success_with_output_round_032(monkeypatch, tmp_path):
    # Ensure settings point to simple values
    monkeypatch.setattr(factor_mod, "FACTOR_COSTEER_SETTINGS", SimpleNamespace(
        data_folder_debug=str(tmp_path / "debugdata"),
        data_folder=str(tmp_path / "data"),
        python_bin="/bin/true",
        file_based_execution_timeout=1,
    ))

    inst = make_instance(tmp_path, file_dict={"factor.py": "print('x')"}, version=1, raise_exception=False)

    # Make a dummy result file so existence check passes
    (tmp_path / "result.h5").write_text("dummy")

    dummy_df = pd.DataFrame({"a": [1, 2, 3]})
    monkeypatch.setattr(pd, "read_hdf", lambda p: dummy_df)

    # subprocess succeeds
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: b"ok")

    feedback, df = factor_mod.FactorFBWorkspace.execute.__wrapped__(inst, "Debug")
    assert factor_mod.FactorFBWorkspace.FB_OUTPUT_FILE_FOUND in feedback
    # and the returned dataframe is our dummy
    pd.testing.assert_frame_equal(df, dummy_df)


def test_version1_subprocess_called_error_truncate_round_032(monkeypatch, tmp_path):
    inst = make_instance(tmp_path, file_dict={"factor.py": "print('x')"}, version=1, raise_exception=True)

    # Create very long error output to trigger truncation
    long_bytes = b"A" * 3000
    def raise_called(*a, **k):
        raise subprocess.CalledProcessError(returncode=2, cmd=a[0] if a else "cmd", output=long_bytes)

    monkeypatch.setattr(subprocess, "check_output", raise_called)

    with pytest.raises(CustomRuntimeError) as excinfo:
        factor_mod.FactorFBWorkspace.execute.__wrapped__(inst, "Debug")
    msg = str(excinfo.value)
    assert "....hidden long error message...." in msg
    # truncated result should be shorter than original long output
    assert len(msg) < len(long_bytes)


def test_timeout_behavior_no_raise_round_032(monkeypatch, tmp_path):
    # Setup settings timeout string for assertion
    monkeypatch.setattr(factor_mod, "FACTOR_COSTEER_SETTINGS", SimpleNamespace(
        data_folder_debug=str(tmp_path / "debugdata"),
        data_folder=str(tmp_path / "data"),
        python_bin="/bin/true",
        file_based_execution_timeout=5,
    ))

    inst = make_instance(tmp_path, file_dict={"factor.py": "print('x')"}, version=1, raise_exception=False)

    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd=a[0] if a else "cmd", timeout=5)

    monkeypatch.setattr(subprocess, "check_output", raise_timeout)

    feedback, df = factor_mod.FactorFBWorkspace.execute.__wrapped__(inst, "Debug")
    assert "Execution timeout error" in feedback
    assert str(factor_mod.FACTOR_COSTEER_SETTINGS.file_based_execution_timeout) in feedback or "timeout" in feedback
    assert df is None


def test_version2_template_written_round_032(monkeypatch, tmp_path):
    # Version 2 uses KAGGLE_IMPLEMENT_SETTING and writes a temporary execution script
    monkeypatch.setattr(factor_mod, "KAGGLE_IMPLEMENT_SETTING", SimpleNamespace(
        local_data_path=str(tmp_path / "kaggle_local"),
        competition="comp",
    ))
    monkeypatch.setattr(factor_mod, "FACTOR_COSTEER_SETTINGS", SimpleNamespace(
        data_folder_debug=str(tmp_path / "debugdata"),
        data_folder=str(tmp_path / "data"),
        python_bin="/bin/true",
        file_based_execution_timeout=1,
    ))

    inst = make_instance(tmp_path, file_dict={"factor.py": "print('x')"}, version=2, raise_exception=False)

    # Patch Path.read_text used for reading the template to avoid filesystem dependency
    original_read_text = Path.read_text
    def fake_read_text(self, *a, **k):
        # If reading the module template file, return simple python code
        if self.name == "factor_execution_template.txt":
            return "print(\"hello\")"
        return original_read_text(self, *a, **k)

    monkeypatch.setattr(factor_mod.Path, "read_text", fake_read_text)

    # Make a dummy result file so existence check passes
    (tmp_path / "result.h5").write_text("dummy")
    dummy_df = pd.DataFrame({"b": [7, 8]})
    monkeypatch.setattr(pd, "read_hdf", lambda p: dummy_df)

    # subprocess succeeds
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: b"ok")

    feedback, df = factor_mod.FactorFBWorkspace.execute.__wrapped__(inst, "NotDebug")
    assert factor_mod.FactorFBWorkspace.FB_OUTPUT_FILE_FOUND in feedback
    pd.testing.assert_frame_equal(df, dummy_df)
