import types
import pytest
from types import SimpleNamespace

from pr_agent.tools.pr_description import PRDescription
import pr_agent.tools.pr_description as pr_description_mod


class _DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        # Keep deterministic capture of error calls
        self.errors.append(str(msg))


def _make_settings(publish_labels: bool):
    # Minimal settings shape used by _prepare_labels only (publish_labels flag)
    s = SimpleNamespace()
    s.pr_description = SimpleNamespace(publish_labels=publish_labels)
    return s


def test_labels_list_round_051(monkeypatch):
    """Branch: 'labels' present and is a list -> use list and strip elements"""
    monkeypatch.setattr(pr_description_mod, "get_settings", lambda: _make_settings(False))
    monkeypatch.setattr(pr_description_mod, "get_logger", lambda: _DummyLogger())

    # Use __new__ to avoid executing __init__ which constructs providers
    p = PRDescription.__new__(PRDescription)
    # prepare attributes used by _prepare_labels
    p.data = {"labels": [" bug ", "Feature "]}
    p.variables = {}
    p.pr_id = "PR-1"

    # Act
    result = p._prepare_labels()

    # Assert
    assert result == ["bug", "Feature"], "List labels should be trimmed but preserve original case"


def test_labels_str_round_051(monkeypatch):
    """Branch: 'labels' present and is a str -> split by comma and strip"""
    monkeypatch.setattr(pr_description_mod, "get_settings", lambda: _make_settings(False))
    monkeypatch.setattr(pr_description_mod, "get_logger", lambda: _DummyLogger())

    p = PRDescription.__new__(PRDescription)
    p.data = {"labels": " bug, enhancement ,Fix "}
    p.variables = {}
    p.pr_id = "PR-2"

    result = p._prepare_labels()

    assert result == ["bug", "enhancement", "Fix"]


def test_type_list_publish_round_051(monkeypatch):
    """Branch: no 'labels' but 'type' is a list and publish_labels True -> use type list"""
    monkeypatch.setattr(pr_description_mod, "get_settings", lambda: _make_settings(True))
    monkeypatch.setattr(pr_description_mod, "get_logger", lambda: _DummyLogger())

    p = PRDescription.__new__(PRDescription)
    p.data = {"type": [" doc ", " test"]}
    p.variables = {}
    p.pr_id = "PR-3"

    result = p._prepare_labels()

    assert result == ["doc", "test"]


def test_type_str_publish_round_051(monkeypatch):
    """Branch: no 'labels' but 'type' is a str and publish_labels True -> split and strip"""
    monkeypatch.setattr(pr_description_mod, "get_settings", lambda: _make_settings(True))
    monkeypatch.setattr(pr_description_mod, "get_logger", lambda: _DummyLogger())

    p = PRDescription.__new__(PRDescription)
    p.data = {"type": "one, two,three"}
    p.variables = {}
    p.pr_id = "PR-4"

    result = p._prepare_labels()

    assert result == ["one", "two", "three"]


def test_labels_conversion_round_051(monkeypatch):
    """Branch: conversion using labels_minimal_to_labels_dict replaces lowercased keys with original case"""
    monkeypatch.setattr(pr_description_mod, "get_settings", lambda: _make_settings(False))
    monkeypatch.setattr(pr_description_mod, "get_logger", lambda: _DummyLogger())

    p = PRDescription.__new__(PRDescription)
    # simulate label coming in lowercase minimal form
    p.data = {"labels": ["bug", "perf"]}
    p.variables = {"labels_minimal_to_labels_dict": {"bug": "Bug", "perf": "Performance"}}
    p.pr_id = "PR-5"

    result = p._prepare_labels()

    assert result == ["Bug", "Performance"]


def test_labels_conversion_exception_round_051(monkeypatch):
    """Exception path inside conversion triggers logger.error with pr_id included"""
    dummy_logger = _DummyLogger()
    monkeypatch.setattr(pr_description_mod, "get_settings", lambda: _make_settings(False))
    # patch get_logger to return our dummy logger so we can inspect error calls
    monkeypatch.setattr(pr_description_mod, "get_logger", lambda: dummy_logger)

    p = PRDescription.__new__(PRDescription)
    p.data = {"labels": ["bug"]}
    # set a value that will raise when checking 'in' (None -> TypeError)
    p.variables = {"labels_minimal_to_labels_dict": None}
    p.pr_id = "PR-EXC"

    result = p._prepare_labels()

    # labels should still be returned trimmed
    assert result == ["bug"]

    # and logger.error must have been called with a message containing the pr_id and the 'Error converting' prefix
    assert any("Error converting labels to original case" in e and "PR-EXC" in e for e in dummy_logger.errors), (
        "Expected logger.error to be called with conversion error mentioning pr_id"
    )
