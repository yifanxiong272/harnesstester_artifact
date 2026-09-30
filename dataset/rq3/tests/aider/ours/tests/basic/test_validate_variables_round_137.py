import pytest
import aider.models as models


def test_validate_variables_all_present_round_137(monkeypatch):
    # Patch the os.environ used by the module so membership checks are deterministic
    monkeypatch.setattr(models.os, "environ", {"A": "1", "B": "2"})

    result = models.validate_variables(["A", "B"])

    # When all requested vars are present, missing_keys should be an empty list
    # and keys_in_environment should be True
    assert isinstance(result, dict)
    assert result["keys_in_environment"] is True
    assert result["missing_keys"] == []


def test_validate_variables_some_missing_round_137(monkeypatch):
    # Only 'A' is present; 'B' and 'C' should be reported missing in order
    monkeypatch.setattr(models.os, "environ", {"A": "1"})

    result = models.validate_variables(["A", "B", "C"])

    assert isinstance(result, dict)
    # missing list is truthy -> keys_in_environment should be False
    assert result["keys_in_environment"] is False
    # Ensure the missing keys list contains the missing entries in the loop order
    assert result["missing_keys"] == ["B", "C"]


def test_validate_variables_empty_list_round_137(monkeypatch):
    # Even if environment has unrelated keys, asking for an empty vars list should
    # return keys_in_environment=True and an empty missing_keys list
    monkeypatch.setattr(models.os, "environ", {"UNRELATED": "x"})

    result = models.validate_variables([])

    assert result == {"keys_in_environment": True, "missing_keys": []}
