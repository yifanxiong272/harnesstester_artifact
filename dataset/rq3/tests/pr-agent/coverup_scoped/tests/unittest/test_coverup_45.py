# file: pr_agent/tools/pr_generate_labels.py:159-180
# asked: {"lines": [160, 163, 164, 165, 166, 167, 168, 171, 172, 173, 174, 175, 176, 177, 178, 180], "branches": [[163, 164], [163, 168], [164, 165], [164, 166], [166, 167], [166, 168], [172, 173], [172, 180], [174, 175], [174, 180], [175, 174], [175, 176]]}
# gained: {"lines": [160, 163, 164, 165, 166, 167, 168, 171, 172, 173, 174, 175, 176, 177, 178, 180], "branches": [[163, 164], [164, 165], [164, 166], [166, 167], [172, 173], [172, 180], [174, 175], [174, 180], [175, 174], [175, 176]]}

import pytest
from pr_agent.tools import pr_generate_labels
from pr_agent.tools.pr_generate_labels import PRGenerateLabels


def make_instance():
    # Create instance without calling __init__
    inst = object.__new__(PRGenerateLabels)
    return inst


def test_prepare_labels_list_and_mapping():
    inst = make_instance()
    inst.data = {'labels': [' bug ', 'feature', '  UNKNOWN  ']}
    inst.variables = {
        'labels_minimal_to_labels_dict': {
            'bug': 'Bug',
            'feature': 'Feature',
            # UNKNOWN intentionally not mapped
        }
    }
    inst.pr_id = 101

    result = inst._prepare_labels()

    assert result == ['Bug', 'Feature', 'UNKNOWN']


def test_prepare_labels_string_split_and_strip():
    inst = make_instance()
    inst.data = {'labels': '  alpha, beta ,gamma  ,delta'}
    inst.variables = {}  # no mapping present
    inst.pr_id = 'str-test'

    result = inst._prepare_labels()

    assert result == ['alpha', 'beta', 'gamma', 'delta']


def test_prepare_labels_handles_exception_in_variables(monkeypatch):
    class BadVars:
        def __contains__(self, key):
            raise RuntimeError("boom in __contains__")

    inst = make_instance()
    inst.data = {'labels': ['x ', ' y']}
    inst.variables = BadVars()
    inst.pr_id = 'PR-EXC-1'

    logged = {}

    class DummyLogger:
        def error(self, msg):
            logged['msg'] = msg

    # Patch the get_logger used inside the module
    monkeypatch.setattr(pr_generate_labels, 'get_logger', lambda: DummyLogger())

    result = inst._prepare_labels()

    assert result == ['x', 'y']
    assert 'PR-EXC-1' in logged.get('msg', '')
    assert 'Error converting labels to original case' in logged.get('msg', '')
