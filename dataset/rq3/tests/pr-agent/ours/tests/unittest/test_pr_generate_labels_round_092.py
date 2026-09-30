import pytest
from pr_agent.tools.pr_generate_labels import PRGenerateLabels
import pr_agent.tools.pr_generate_labels as pr_mod

class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        # store messages for assertions
        self.errors.append(msg)


def _make_instance():
    # create instance without calling __init__ to avoid needing external dependencies
    inst = object.__new__(PRGenerateLabels)
    inst.pr_id = "PR-1"
    return inst


def test_no_labels_round_092(monkeypatch):
    """No 'labels' key: should return empty list and not log an error."""
    logger = DummyLogger()
    monkeypatch.setattr(pr_mod, "get_logger", lambda: logger)

    inst = _make_instance()
    inst.data = {}
    inst.variables = {}

    res = inst._prepare_labels()

    assert res == []
    assert logger.errors == []


def test_labels_list_and_mapping_round_092(monkeypatch):
    """When labels is a list and a mapping exists, items should be replaced by mapping values."""
    logger = DummyLogger()
    monkeypatch.setattr(pr_mod, "get_logger", lambda: logger)

    inst = _make_instance()
    inst.data = {"labels": ["bug", "feat"]}
    inst.variables = {"labels_minimal_to_labels_dict": {"bug": "Bug", "feat": "Feature"}}

    res = inst._prepare_labels()

    assert res == ["Bug", "Feature"]
    assert logger.errors == []


def test_labels_string_and_strip_round_092(monkeypatch):
    """When labels is a comma string, it should be split and stripped."""
    logger = DummyLogger()
    monkeypatch.setattr(pr_mod, "get_logger", lambda: logger)

    inst = _make_instance()
    inst.data = {"labels": " bug,feat ,  chore "}
    inst.variables = {}

    res = inst._prepare_labels()

    assert res == ["bug", "feat", "chore"]
    assert logger.errors == []


def test_mapping_exception_round_092(monkeypatch):
    """If accessing the mapping raises, the exception is caught and logged; labels remain unchanged."""
    logger = DummyLogger()
    monkeypatch.setattr(pr_mod, "get_logger", lambda: logger)

    class BadVars:
        # make 'in' return True so the code will try to index into the mapping
        def __contains__(self, key):
            return True

        # raise when trying to get the mapping to trigger the except branch
        def __getitem__(self, key):
            raise RuntimeError("boom")

    inst = _make_instance()
    inst.data = {"labels": ["x"]}
    inst.variables = BadVars()

    res = inst._prepare_labels()

    # labels unchanged because mapping lookup failed
    assert res == ["x"]

    # ensure error was logged and contains pr_id and original exception message
    assert len(logger.errors) == 1
    logged = logger.errors[0]
    assert "Error converting labels to original case" in logged
    assert "PR-1" in logged
    assert "boom" in logged
