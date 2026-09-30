import types
import pytest

import pr_agent.algo.utils as utils
from pr_agent.algo.utils import set_custom_labels


class FakeSettings:
    def __init__(self, enable_custom_labels: bool, labels):
        # mirror the shape used in utils: an object with .config.enable_custom_labels
        self.config = types.SimpleNamespace(enable_custom_labels=enable_custom_labels)
        self._labels = labels

    def get(self, key, default=None):
        if key == 'custom_labels':
            return self._labels
        return default


def test_disable_custom_labels_round_114(monkeypatch):
    """
    When enable_custom_labels is False, set_custom_labels should return early
    and not mutate the provided variables dict.
    """
    fake = FakeSettings(enable_custom_labels=False, labels={})
    monkeypatch.setattr(utils, 'get_settings', lambda: fake)

    variables = {"existing": 1}
    result = set_custom_labels(variables)

    # function returns None and does not alter variables except what existed before
    assert result is None
    assert variables == {"existing": 1}


def test_default_labels_round_114(monkeypatch):
    """
    When enable_custom_labels is True but get('custom_labels') yields an empty/falsy value,
    the function should set a default multiline "custom_labels" string starting with
    the first default label and containing all defaults separated by newlines.
    """
    fake = FakeSettings(enable_custom_labels=True, labels={})
    monkeypatch.setattr(utils, 'get_settings', lambda: fake)

    variables = {}
    result = set_custom_labels(variables)

    assert result is None
    assert "custom_labels" in variables
    custom = variables["custom_labels"]

    # Should start with the first default label with the exact leading indent used in code
    assert custom.startswith("      - Bug fix")

    # Should contain each default label from the source
    for expected_label in ['Bug fix', 'Tests', 'Bug fix with tests', 'Enhancement', 'Documentation', 'Other']:
        assert expected_label in custom


def test_custom_labels_dict_round_114(monkeypatch):
    """
    Provide a custom labels mapping and verify that:
    - variables["custom_labels_class"] is initialized and lines for each key are appended
      with keys lowercased and spaces replaced by underscores
    - newline characters inside descriptions are escaped as "\\n" and wrapped in single quotes
    - variables["labels_minimal_to_labels_dict"] maps minimal keys back to original labels
    """
    # include a trailing newline in one description to exercise .strip('\n') behavior
    labels = {
        'Bug Fix': {'description': 'Fixes bug\nMore\n'},
        'New Feature': {'description': 'Adds feature'}
    }
    fake = FakeSettings(enable_custom_labels=True, labels=labels)
    monkeypatch.setattr(utils, 'get_settings', lambda: fake)

    variables = {}
    result = set_custom_labels(variables)

    assert result is None

    # Validate custom_labels_class content
    assert "custom_labels_class" in variables
    cls_str = variables["custom_labels_class"]

    # It must start with the class declaration
    assert cls_str.startswith("class Label(str, Enum):")

    # Key names should be normalized: 'Bug Fix' -> 'bug_fix', 'New Feature' -> 'new_feature'
    assert "\n    bug_fix = 'Fixes bug\\nMore'" in cls_str
    assert "\n    new_feature = 'Adds feature'" in cls_str

    # Validate the mapping from minimal keys to original labels
    assert variables.get("labels_minimal_to_labels_dict") == {
        'bug_fix': 'Bug Fix',
        'new_feature': 'New Feature'
    }
