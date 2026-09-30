# file: aider/models.py:1267-1299
# asked: {"lines": [1268, 1270, 1272, 1274, 1275, 1276, 1277, 1278, 1281, 1283, 1284, 1285, 1286, 1287, 1288, 1290, 1293, 1294, 1295, 1296, 1299], "branches": [[1275, 1276], [1275, 1277], [1281, 1283], [1281, 1293], [1284, 1285], [1284, 1288], [1286, 1284], [1286, 1287]]}
# gained: {"lines": [1268, 1270, 1272, 1274, 1275, 1276, 1277, 1278, 1281, 1283, 1284, 1285, 1286, 1287, 1288, 1290, 1293, 1294, 1295, 1296, 1299], "branches": [[1275, 1276], [1275, 1277], [1281, 1283], [1281, 1293], [1284, 1285], [1284, 1288], [1286, 1284], [1286, 1287]]}

import re
from dataclasses import dataclass
import aider.models as models
from aider.models import get_model_settings_as_yaml


def _make_model_settings_class():
    @dataclass
    class ModelSettings:
        name: str = ""
        version: int = 1
        enabled: bool = False
        tags: list = None

        def __post_init__(self):
            # Ensure a deterministic default for tags that matches the declared default
            if self.tags is None:
                self.tags = []
    return ModelSettings


def test_get_model_settings_as_yaml_with_entries(monkeypatch):
    # Prepare a dataclass and two instances to exercise sorting and filtering
    ModelSettings = _make_model_settings_class()
    ms_a = ModelSettings(name="a")  # only name differs from default
    ms_b = ModelSettings(name="b", enabled=True)  # enabled differs from default too

    # Patch the module globals used by the function
    monkeypatch.setattr(models, "ModelSettings", ModelSettings, raising=True)
    monkeypatch.setattr(models, "MODEL_SETTINGS", [ms_b, ms_a], raising=True)

    yaml_str = get_model_settings_as_yaml()

    # The YAML should contain the default entry first with '(default values)'
    assert "(default values)" in yaml_str
    # Defaults should show all default fields (version, enabled, tags)
    assert "version: 1" in yaml_str
    assert "enabled: false" in yaml_str
    assert "tags:" in yaml_str

    # The two model entries should be present and sorted by name ('a' then 'b')
    assert "\n\n- name: a" in yaml_str, "Expected blank line then '- name: a' block"
    assert "\n\n- name: b" in yaml_str, "Expected blank line then '- name: b' block"

    # The 'b' entry should include enabled: true
    # Ensure 'enabled: true' exists (and not only in default block)
    assert "enabled: true" in yaml_str

    # Ensure that the 'a' entry does not redundantly include default fields (only name)
    # Find the 'a' block and ensure it contains only 'name'
    # We split on occurrences of "\n\n- " which is how the function formats blocks after replacement
    blocks = yaml_str.split("\n\n- ")
    # First block begins with '- name:' so adjust
    # Normalize blocks to start with '- ' for consistent parsing
    normalized_blocks = []
    for i, b in enumerate(blocks):
        if i == 0:
            normalized_blocks.append(b)
        else:
            normalized_blocks.append("- " + b)
    # Find block that has "name: a"
    a_block = next((b for b in normalized_blocks if "name: a" in b), None)
    assert a_block is not None
    # The 'a' block should not contain 'enabled:' or 'version:' lines (those are defaults)
    assert "enabled:" not in a_block or "enabled: true" not in a_block
    assert "version:" not in a_block


def test_get_model_settings_as_yaml_with_no_entries(monkeypatch):
    # Ensure behavior when MODEL_SETTINGS is empty: only defaults should appear
    ModelSettings = _make_model_settings_class()

    monkeypatch.setattr(models, "ModelSettings", ModelSettings, raising=True)
    monkeypatch.setattr(models, "MODEL_SETTINGS", [], raising=True)

    yaml_str = get_model_settings_as_yaml()

    # Should contain default block with marker
    assert "(default values)" in yaml_str
    # Since there are no additional entries, there should be no double-newline entry separators
    assert "\n\n- " not in yaml_str
    # And the output should start with the list item for the defaults
    assert yaml_str.lstrip().startswith("- name: (default values)") or yaml_str.startswith("- name: (default values)")
