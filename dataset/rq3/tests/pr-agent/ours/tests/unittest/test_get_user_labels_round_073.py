import pytest

from pr_agent.algo import utils


class DummySettings:
    def __init__(self, enable_custom_labels=False, custom_labels=None):
        self.config = {"enable_custom_labels": enable_custom_labels}
        self._custom = custom_labels or []

    def get(self, name, default=None):
        if name == "custom_labels":
            return self._custom
        return default


class DummyLogger:
    def __init__(self):
        self.debug_calls = []
        self.exception_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def exception(self, msg):
        self.exception_calls.append(msg)


def test_get_user_labels_filters_known_and_calls_debug_round_073(monkeypatch):
    # Setup settings: custom labels disabled
    settings = DummySettings(enable_custom_labels=False, custom_labels=["should_not_matter"]) 
    logger = DummyLogger()

    monkeypatch.setattr(utils, "get_settings", lambda: settings)
    monkeypatch.setattr(utils, "get_logger", lambda: logger)

    current = ["Bug Fix", "newFeature", "documentation"]
    result = utils.get_user_labels(current)

    # Only 'newFeature' should remain because 'Bug Fix' and 'documentation' are filtered
    assert result == ["newFeature"]

    # When user_labels is non-empty, debug should be called exactly once with the formatted list
    assert len(logger.debug_calls) == 1
    assert logger.debug_calls[0] == "Keeping user labels: ['newFeature']"
    assert logger.exception_calls == []


def test_get_user_labels_respects_custom_labels_round_073(monkeypatch):
    # Setup settings: custom labels enabled, and 'keepme' is defined as a custom label -> it should be skipped
    settings = DummySettings(enable_custom_labels=True, custom_labels=["keepme"])
    logger = DummyLogger()

    monkeypatch.setattr(utils, "get_settings", lambda: settings)
    monkeypatch.setattr(utils, "get_logger", lambda: logger)

    current = ["keepme", "user_added_label"]
    result = utils.get_user_labels(current)

    # 'keepme' is in configured custom_labels and should be skipped when enable_custom_labels is True
    assert result == ["user_added_label"]
    # debug is called because user_labels is non-empty
    assert logger.debug_calls == ["Keeping user labels: ['user_added_label']"]
    assert logger.exception_calls == []


def test_get_user_labels_handles_none_current_round_073(monkeypatch):
    # current_labels None should be treated as empty list and return empty list
    settings = DummySettings(enable_custom_labels=False, custom_labels=[])
    logger = DummyLogger()

    monkeypatch.setattr(utils, "get_settings", lambda: settings)
    monkeypatch.setattr(utils, "get_logger", lambda: logger)

    result = utils.get_user_labels(None)

    assert result == []
    # No debug or exception calls because nothing to keep and no error
    assert logger.debug_calls == []
    assert logger.exception_calls == []


def test_get_user_labels_exception_returns_current_labels_and_logs_exception_round_073(monkeypatch):
    # Make get_settings raise to force exception path
    def raising_get_settings():
        raise RuntimeError("boom")

    logger = DummyLogger()
    monkeypatch.setattr(utils, "get_settings", raising_get_settings)
    monkeypatch.setattr(utils, "get_logger", lambda: logger)

    current = ["labelA"]
    result = utils.get_user_labels(current)

    # On exception the function should return the original current_labels
    assert result == current

    # And logger.exception should have been called with a message containing the exception text
    assert len(logger.exception_calls) == 1
    assert "Failed to get user labels" in logger.exception_calls[0]
    assert "boom" in logger.exception_calls[0]
