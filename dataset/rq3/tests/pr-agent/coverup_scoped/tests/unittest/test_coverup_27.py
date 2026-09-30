# file: pr_agent/tools/pr_description.py:470-495
# asked: {"lines": [471, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 487, 488, 489, 490, 491, 492, 493, 494, 495], "branches": [[474, 475], [474, 479], [475, 476], [475, 477], [477, 478], [477, 484], [479, 480], [479, 484], [480, 481], [480, 482], [482, 483], [482, 484], [488, 489], [488, 495], [490, 491], [490, 495], [491, 490], [491, 492]]}
# gained: {"lines": [471, 474, 475, 476, 479, 480, 482, 483, 484, 487, 488, 489, 490, 491, 492, 493, 494, 495], "branches": [[474, 475], [474, 479], [475, 476], [479, 480], [480, 482], [482, 483], [488, 489], [488, 495], [490, 491], [490, 495], [491, 490], [491, 492]]}

import pytest
from types import SimpleNamespace

import pr_agent.tools.pr_description as pr_desc_mod


def _call_prepare_labels_with(fake_self):
    return pr_desc_mod.PRDescription._prepare_labels(fake_self)


def test_prepare_labels_with_labels_list_and_mapping(monkeypatch):
    # Patch the get_settings and get_logger in the module under test (pr_agent.tools.pr_description)
    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: SimpleNamespace(pr_description=SimpleNamespace(publish_labels=False)))
    monkeypatch.setattr(pr_desc_mod, "get_logger", lambda: SimpleNamespace(error=lambda *a, **k: None))

    fake = SimpleNamespace()
    fake.data = {"labels": [" bug ", "Feature", "unchanged"]}
    fake.variables = {
        "labels_minimal_to_labels_dict": {
            "bug": "Bug",
        }
    }
    fake.pr_id = 123

    result = _call_prepare_labels_with(fake)
    assert result == ["Bug", "Feature", "unchanged"]


def test_prepare_labels_with_type_string_and_publish_labels_true(monkeypatch):
    # Patch the get_settings in the module under test so the 'type' branch is considered
    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: SimpleNamespace(pr_description=SimpleNamespace(publish_labels=True)))
    monkeypatch.setattr(pr_desc_mod, "get_logger", lambda: SimpleNamespace(error=lambda *a, **k: None))

    fake = SimpleNamespace()
    fake.data = {"type": "one, two ,three"}
    fake.variables = {}
    fake.pr_id = "PR-1"

    result = _call_prepare_labels_with(fake)
    assert result == ["one", "two", "three"]


def test_prepare_labels_handles_exception_and_logs_error(monkeypatch):
    # Ensure the module's get_settings is present (not used here) and capture logger.error
    monkeypatch.setattr(pr_desc_mod, "get_settings", lambda: SimpleNamespace(pr_description=SimpleNamespace(publish_labels=True)))

    logged = []
    class DummyLogger:
        def error(self, msg):
            logged.append(msg)

    monkeypatch.setattr(pr_desc_mod, "get_logger", lambda: DummyLogger())

    fake = SimpleNamespace()
    fake.data = {"labels": [" alpha ", "beta"]}
    # make variables None so "'labels_minimal_to_labels_dict' in self.variables" raises
    fake.variables = None
    fake.pr_id = "X-999"

    result = _call_prepare_labels_with(fake)

    assert result == ["alpha", "beta"]
    assert logged, "Expected logger.error to be called"
    assert any("Error converting labels to original case" in m and "X-999" in m for m in logged)
