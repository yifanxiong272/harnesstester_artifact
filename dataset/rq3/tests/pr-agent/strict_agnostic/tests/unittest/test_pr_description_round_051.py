import pytest
from types import SimpleNamespace
import pr_agent.tools.pr_description as pd
from pr_agent.tools.pr_description import PRDescription

class _BadMapping:
    def __contains__(self, key):
        # membership check will raise to trigger the exception handling path
        raise RuntimeError("boom")


def _make_instance(data, variables=None, pr_id="PR-1"):
    # create instance without invoking __init__ to avoid external side effects
    inst = PRDescription.__new__(PRDescription)
    inst.data = data
    inst.variables = variables or {}
    inst.pr_id = pr_id
    return inst


def test_labels_list_round_051():
    # branch: 'labels' present and is list -> assigned directly, then stripped
    inst = _make_instance({"labels": [" bug ", "Enhancement"]})
    res = inst._prepare_labels()
    assert res == ["bug", "Enhancement"]


def test_labels_string_round_051():
    # branch: 'labels' present and is str -> split by comma and strip
    inst = _make_instance({"labels": " bug,feature "})
    res = inst._prepare_labels()
    assert res == ["bug", "feature"]


def test_type_list_and_publish_round_051(monkeypatch):
    # branch: no 'labels', 'type' present as list and publish_labels True
    monkeypatch.setattr(pd, "get_settings", lambda: SimpleNamespace(pr_description=SimpleNamespace(publish_labels=True)))
    # include a minimal mapping to check conversion from minimal->original case
    variables = {"labels_minimal_to_labels_dict": {"a": "A"}}
    inst = _make_instance({"type": [" a ", "B"]}, variables=variables)
    res = inst._prepare_labels()
    # ' a ' should be stripped to 'a' then replaced via mapping -> 'A'
    assert res == ["A", "B"]


def test_type_string_no_publish_round_051(monkeypatch):
    # branch: no 'labels', 'type' present but publish_labels False -> ignored
    monkeypatch.setattr(pd, "get_settings", lambda: SimpleNamespace(pr_description=SimpleNamespace(publish_labels=False)))
    inst = _make_instance({"type": "x,y"})
    res = inst._prepare_labels()
    assert res == []


def test_variables_exception_logs_round_051(monkeypatch):
    # branch: variables contains labels_minimal_to_labels_dict but membership check raises
    class LoggerStub:
        def __init__(self):
            self.errs = []
        def error(self, msg):
            self.errs.append(msg)

    logger = LoggerStub()
    # patch get_logger in the module to return our stub so we can assert an error was logged
    monkeypatch.setattr(pd, "get_logger", lambda: logger)

    inst = _make_instance({"labels": ["one"]}, variables={"labels_minimal_to_labels_dict": _BadMapping()}, pr_id="PR-EX")
    res = inst._prepare_labels()
    # mapping raised, but function should catch and return the original stripped label
    assert res == ["one"]
    # logger.error should have been called with the PR id included in the message
    assert any("Error converting labels to original case PR-EX" in m for m in logger.errs)
