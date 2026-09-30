# file: aider/main.py:43-57
# asked: {"lines": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57], "branches": [[45, 46], [45, 57], [46, 45], [46, 47], [49, 45], [49, 50], [50, 49], [50, 51]]}
# gained: {"lines": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57], "branches": [[45, 46], [45, 57], [46, 45], [46, 47], [49, 45], [49, 50], [50, 49], [50, 51]]}

import builtins
from pathlib import Path

import pytest

from aider.main import check_config_files_for_yes


def test_detect_yes_reports_and_returns_true(tmp_path, capsys):
    # Create a config file that contains a line starting with 'yes:'
    cfg = tmp_path / "config_with_yes.cfg"
    cfg.write_text("some: value\nyes: should-be-replaced\nanother: line\n")

    # Also include a non-existent file path to ensure it's ignored
    nonexist = tmp_path / "does_not_exist.cfg"

    result = check_config_files_for_yes([str(cfg), str(nonexist)])
    captured = capsys.readouterr()

    assert result is True
    # Verify printed messages include expected content
    assert "Configuration error detected." in captured.out
    assert f"The file {str(cfg)} contains a line starting with 'yes:'" in captured.out
    assert "Please replace 'yes:' with 'yes-always:' in this file." in captured.out


def test_open_exception_is_handled_and_returns_false(tmp_path, monkeypatch, capsys):
    # Create a config file that we'll make fail on open
    bad_cfg = tmp_path / "bad.cfg"
    bad_cfg.write_text("no relevant lines here\n")

    # Keep reference to real open
    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        # Normalize to Path for comparison (path may be a Path object or str)
        p = Path(path)
        if p == bad_cfg:
            raise IOError("simulated open failure")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    # Ensure that the function handles the exception and returns False (no 'yes:' found)
    result = check_config_files_for_yes([str(bad_cfg)])
    captured = capsys.readouterr()

    assert result is False
    # No output should be produced because file open failed and exception is swallowed
    assert captured.out == ""
