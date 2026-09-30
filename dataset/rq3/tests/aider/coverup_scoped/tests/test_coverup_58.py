# file: aider/models.py:1121-1128
# asked: {"lines": [1122, 1123, 1124, 1125, 1126, 1127, 1128], "branches": [[1123, 1124], [1123, 1126], [1124, 1123], [1124, 1125], [1126, 1127], [1126, 1128]]}
# gained: {"lines": [1122, 1123, 1124, 1125, 1126, 1127, 1128], "branches": [[1123, 1124], [1123, 1126], [1124, 1123], [1124, 1125], [1126, 1127], [1126, 1128]]}

import os
import pytest

from aider.models import validate_variables


def test_validate_variables_all_present(monkeypatch):
    # Arrange: ensure both variables are present in the environment
    monkeypatch.setenv("TEST_VALIDATE_VAR1", "value1")
    monkeypatch.setenv("TEST_VALIDATE_VAR2", "")  # empty string still counts as present

    vars_to_check = ["TEST_VALIDATE_VAR1", "TEST_VALIDATE_VAR2"]
    # Act
    result = validate_variables(vars_to_check)

    # Assert
    assert isinstance(result, dict)
    assert result["keys_in_environment"] is True
    assert result["missing_keys"] == []

    # Cleanup handled by monkeypatch fixture


def test_validate_variables_some_missing(monkeypatch):
    # Arrange: one present, one missing
    monkeypatch.setenv("TEST_VALIDATE_PRESENT", "1")
    # Ensure missing var is not in environment
    monkeypatch.delenv("TEST_VALIDATE_MISSING", raising=False)

    vars_to_check = ["TEST_VALIDATE_PRESENT", "TEST_VALIDATE_MISSING"]
    # Act
    result = validate_variables(vars_to_check)

    # Assert: keys_in_environment should be False and missing_keys contains the missing var
    assert result["keys_in_environment"] is False
    assert result["missing_keys"] == ["TEST_VALIDATE_MISSING"]


def test_validate_variables_empty_list(monkeypatch):
    # Arrange: no variables to check
    vars_to_check = []
    # Act
    result = validate_variables(vars_to_check)

    # Assert: with no variables, keys_in_environment should be True and missing_keys empty
    assert result == {"keys_in_environment": True, "missing_keys": []}
