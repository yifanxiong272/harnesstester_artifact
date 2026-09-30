import os
from pathlib import Path
import pytest

from aider.main import check_config_files_for_yes


def test_detects_yes_in_file_round_081(tmp_path, capsys):
    # Create a config file that contains a line starting with 'yes:' (with leading whitespace)
    config = tmp_path / "config1.txt"
    config.write_text("some line\n   yes: should-be-changed\nother line\n")

    result = check_config_files_for_yes([str(config)])

    # Function should return True and print the three warning lines
    assert result is True
    captured = capsys.readouterr()
    assert "Configuration error detected." in captured.out
    # exact file path mention
    assert f"The file {str(config)} contains a line starting with 'yes:'" in captured.out
    assert "Please replace 'yes:' with 'yes-always:' in this file." in captured.out


def test_multiple_files_detects_later_yes_round_081(tmp_path, capsys):
    # First file exists but doesn't contain yes:, second contains yes:
    f1 = tmp_path / "a.txt"
    f1.write_text("no relevant content\n")
    f2 = tmp_path / "b.txt"
    f2.write_text("prefix\nyes: present\n")

    result = check_config_files_for_yes([str(f1), str(f2)])

    assert result is True
    captured = capsys.readouterr()
    # Should report the second file specifically
    assert f"The file {str(f2)} contains a line starting with 'yes:'" in captured.out


def test_nonexistent_and_no_yes_round_081(tmp_path, capsys):
    # Pass a non-existent file path -> Path.exists() is False, so ignored
    missing = tmp_path / "no-such-file.txt"

    result = check_config_files_for_yes([str(missing)])

    assert result is False
    captured = capsys.readouterr()
    assert captured.out == ""


def test_open_raises_is_directory_is_caught_round_081(tmp_path, capsys):
    # Create a directory at the path; Path.exists() True but open(path, 'r') will raise IsADirectoryError
    d = tmp_path / "a_dir"
    d.mkdir()

    result = check_config_files_for_yes([str(d)])

    # The IsADirectoryError should be caught by the function and treated as if nothing was found
    assert result is False
    captured = capsys.readouterr()
    assert captured.out == ""
