# file: aider/analytics.py:88-108
# asked: {"lines": [90, 91, 94, 95, 98, 99], "branches": [[89, 90], [93, 94], [97, 98]]}
# gained: {"lines": [90, 91, 94, 95, 98, 99], "branches": [[89, 90], [93, 94], [97, 98]]}

from unittest.mock import Mock

import pytest

import aider.analytics as analytics_mod
from aider.analytics import Analytics


def _new_analytics_instance():
    # Create instance without running __init__
    return object.__new__(Analytics)


def test_enable_no_user_id_calls_disable_with_false_and_ph_remains_none():
    a = _new_analytics_instance()
    # Set attributes used in enable
    a.user_id = None
    a.permanently_disable = False
    a.asked_opt_in = True
    # replace disable with a mock to observe calls
    mock_disable = Mock()
    a.disable = mock_disable

    # Call enable
    a.enable()

    # disable should be called once with False, and ph should remain None (class default)
    mock_disable.assert_called_once_with(False)
    assert getattr(a, "ph") is None


def test_enable_permanently_disable_calls_disable_with_true_and_ph_remains_none():
    a = _new_analytics_instance()
    # Set attributes so first check (user_id) passes, then permanently_disable triggers
    a.user_id = "user-123"
    a.permanently_disable = True
    a.asked_opt_in = True
    mock_disable = Mock()
    a.disable = mock_disable

    a.enable()

    mock_disable.assert_called_once_with(True)
    assert getattr(a, "ph") is None


def test_enable_not_asked_opt_in_calls_disable_with_false_and_ph_remains_none():
    a = _new_analytics_instance()
    # Set attributes so user_id exists and not permanently disabled, but asked_opt_in is False
    a.user_id = "user-123"
    a.permanently_disable = False
    a.asked_opt_in = False
    mock_disable = Mock()
    a.disable = mock_disable

    a.enable()

    mock_disable.assert_called_once_with(False)
    assert getattr(a, "ph") is None


def test_enable_creates_posthog_when_all_conditions_met(monkeypatch):
    a = _new_analytics_instance()
    # Conditions to reach Posthog instantiation
    a.user_id = "user-123"
    a.permanently_disable = False
    a.asked_opt_in = True

    # Ensure predictable module-level fallbacks for project key and host
    monkeypatch.setattr(analytics_mod, "posthog_project_api_key", "proj-key", raising=False)
    monkeypatch.setattr(analytics_mod, "posthog_host", "https://ph.example", raising=False)

    # Provide other attributes/methods referenced
    a.custom_posthog_project_api_key = None
    a.custom_posthog_host = None
    a.posthog_error = lambda e: None
    a.get_system_info = lambda: {"os": "test-os"}

    # Capture Posthog init args
    created = {}

    class FakePosthog:
        def __init__(self, project_api_key, host, on_error, enable_exception_autocapture, super_properties):
            created["project_api_key"] = project_api_key
            created["host"] = host
            created["on_error"] = on_error
            created["enable_exception_autocapture"] = enable_exception_autocapture
            created["super_properties"] = super_properties

    # Monkeypatch the Posthog name in the module to our fake
    monkeypatch.setattr(analytics_mod, "Posthog", FakePosthog)

    # Also ensure disable is present and would raise if called (should not be)
    def disable_should_not_be_called(val):
        raise AssertionError("disable was called unexpectedly")

    a.disable = disable_should_not_be_called

    # Call enable and verify ph created correctly
    a.enable()

    # After enable, instance attribute should be an instance of FakePosthog
    assert isinstance(a.ph, FakePosthog)
    assert created["project_api_key"] == "proj-key"
    assert created["host"] == "https://ph.example"
    assert created["enable_exception_autocapture"] is True
    assert created["super_properties"] == {"os": "test-os"}
