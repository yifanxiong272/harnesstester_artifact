import builtins
import json
from unittest.mock import mock_open
import importlib
import sys

import pytest

# Import the module under test
import gpt_researcher.config.config as config_module
from gpt_researcher.config.config import Config


def _set_default_and_reload(monkeypatch, default_dict):
    """Helper to set DEFAULT_CONFIG in the module under test deterministically."""
    # Patch the DEFAULT_CONFIG in the module so tests can rely on a stable value
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG", default_dict, raising=True)


def test_no_config_path_returns_default_round_074(monkeypatch):
    # Ensure environment has no CONFIG_PATH and DEFAULT_CONFIG is known
    monkeypatch.delenv("CONFIG_PATH", raising=False)
    expected_default = {"alpha": 1}
    _set_default_and_reload(monkeypatch, expected_default)

    result = Config.load_config(None)

    # Should return the DEFAULT_CONFIG object/value we injected
    assert result == expected_default


def test_missing_file_with_suggestion_and_warning_round_074(monkeypatch, capsys):
    # Simulate a non-existent path that does not end with .json
    test_path = "custom-config"
    expected_default = {"k": "v"}
    _set_default_and_reload(monkeypatch, expected_default)

    # Patch os.path.exists used inside the module
    monkeypatch.setattr(config_module.os.path, "exists", lambda p: False)

    # Call and capture prints
    result = Config.load_config(test_path)
    captured = capsys.readouterr()

    # Should have printed both the warning and the suggestion
    assert "Warning: Configuration not found at 'custom-config'" in captured.out
    assert "Do you mean 'custom-config.json'?" in captured.out

    # Should return the default config when file missing
    assert result == expected_default


def test_missing_file_named_default_skips_prints_round_074(monkeypatch, capsys):
    # When config_path == "default" and file missing, prints should be skipped
    test_path = "default"
    expected_default = {"x": 0}
    _set_default_and_reload(monkeypatch, expected_default)

    monkeypatch.setattr(config_module.os.path, "exists", lambda p: False)

    result = Config.load_config(test_path)
    captured = capsys.readouterr()

    # No warning or suggestion printed for the literal "default"
    assert captured.out == ""
    assert result == expected_default


def test_existing_file_merges_with_default_round_074(monkeypatch):
    # When the file exists, its JSON should be merged onto DEFAULT_CONFIG
    test_path = "some/path/config.json"
    default = {"a": 1, "b": 2}
    file_json = {"b": 3, "c": 4}
    expected_merged = {"a": 1, "b": 3, "c": 4}

    _set_default_and_reload(monkeypatch, default)

    # Simulate that the path exists
    monkeypatch.setattr(config_module.os.path, "exists", lambda p: True)

    # Patch builtins.open so json.load reads our data deterministically
    m = mock_open(read_data=json.dumps(file_json))
    monkeypatch.setattr(builtins, "open", m, raising=True)

    # Call load_config and verify merged output
    result = Config.load_config(test_path)
    assert result == expected_merged
