import pytest
from dataclasses import dataclass
import aider.models as models


def test_empty_MODEL_SETTINGS_round_068(monkeypatch):
    """When MODEL_SETTINGS is empty, only the defaults entry should be dumped and
    there should be no inserted blank-line separators (no "\n\n- ").
    """
    @dataclass
    class DummySettings:
        name: str = ""
        a: int = 0
        b: str = "x"

    # Patch the module symbols the function uses
    monkeypatch.setattr(models, "ModelSettings", DummySettings)
    monkeypatch.setattr(models, "MODEL_SETTINGS", [])

    yaml_out = models.get_model_settings_as_yaml()

    # The defaults entry must include the special name override
    assert "(default values)" in yaml_out
    # Because there is only one list item, the replacement for multiple items
    # must not have inserted extra blank lines
    assert "\n\n- " not in yaml_out


def test_model_settings_with_variations_round_068(monkeypatch):
    """Create two model settings where one keeps all defaults and the other
    changes a field value. This exercises the branch that omits default-valued
    fields and the branch that includes changed fields. Also verifies that the
    function adds blank lines between YAML list entries by replacing "\n- "
    with "\n\n- ".
    """
    @dataclass
    class DummySettings:
        name: str = ""
        param1: int = 0
        param2: str = "x"

    # ms_alpha keeps all defaults (so its dict will be empty)
    ms_alpha = DummySettings(name="alpha", param1=0, param2="x")
    # ms_beta changes param1 (so param1 should appear in its dict)
    ms_beta = DummySettings(name="beta", param1=5, param2="x")

    # Patch the module symbols; provide the list in non-sorted order to ensure
    # the function sorts by name internally
    monkeypatch.setattr(models, "ModelSettings", DummySettings)
    monkeypatch.setattr(models, "MODEL_SETTINGS", [ms_beta, ms_alpha])

    yaml_out = models.get_model_settings_as_yaml()

    # The changed field must be present in the YAML output
    assert "param1" in yaml_out
    assert "5" in yaml_out

    # The empty-dict entry for the alpha model should appear as an empty mapping
    # representation in YAML (e.g. "- {}")
    assert "- {}" in yaml_out or "- {}\n" in yaml_out

    # Because there are multiple list entries, the function should have inserted
    # blank lines before subsequent "- " entries
    assert "\n\n- " in yaml_out
