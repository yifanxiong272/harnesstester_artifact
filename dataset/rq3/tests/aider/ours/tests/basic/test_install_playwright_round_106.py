import sys
import types
import pytest

import importlib

import aider.scrape as scrape


class FakeIO:
    def __init__(self, confirm_return=True):
        self.outputs = []
        self.errors = []
        self.confirm_return = confirm_return

    def tool_output(self, text):
        # capture output text shown to the user
        self.outputs.append(text)

    def confirm_ask(self, *args, **kwargs):
        # simulate user confirmation
        return self.confirm_return

    def tool_error(self, msg):
        # capture error messages
        self.errors.append(msg)


def test_install_playwright_both_present_round_106(monkeypatch):
    """If both pip and chromium are present, install_playwright should return True immediately."""
    # Arrange: check_env -> (True, True)
    monkeypatch.setattr(scrape, "check_env", lambda: (True, True))
    io = FakeIO(confirm_return=True)

    # Act
    result = scrape.install_playwright(io)

    # Assert
    assert result is True
    # No messages should have been emitted because early return occurs
    assert io.outputs == []
    assert io.errors == []


def test_install_playwright_no_pip_user_declines_round_106(monkeypatch):
    """When pip is missing and user declines install, the function prints instructions and returns None."""
    # Arrange: pip missing, chromium present
    monkeypatch.setattr(scrape, "check_env", lambda: (False, True))

    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda args: pip_cmd)
    # Ensure the docs URL is predictable
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.local/playwright", raising=False)

    io = FakeIO(confirm_return=False)  # user declines

    # Act
    result = scrape.install_playwright(io)

    # Assert
    # Should have printed the install instructions (tool_output called once)
    assert result is None
    assert len(io.outputs) == 1
    output_text = io.outputs[0]
    # The printed instructions should include the pip command and the enable_playwright URL
    assert "pip install" in output_text or "aider-chat[playwright]" in output_text
    assert "https://example.local/playwright" in output_text
    # No errors were emitted because install was not attempted
    assert io.errors == []


def test_install_playwright_pip_fails_round_106(monkeypatch):
    """When pip install fails, the function should call tool_error and return None."""
    # Arrange: pip missing, chromium present
    monkeypatch.setattr(scrape, "check_env", lambda: (False, True))

    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda args: pip_cmd)
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.local/playwright", raising=False)

    # run_install should fail for pip command
    def fake_run_install(cmd):
        # If pip install command (contains 'aider-chat'), return failure
        if any("aider-chat" in str(p) for p in cmd):
            return (False, "pip failed: out of disk")
        return (True, "ok")

    monkeypatch.setattr(scrape.utils, "run_install", fake_run_install)

    io = FakeIO(confirm_return=True)  # user accepts

    # Act
    result = scrape.install_playwright(io)

    # Assert
    assert result is None
    # tool_error should have been called with the run_install output
    assert any("pip failed: out of disk" in e for e in io.errors)


def test_install_playwright_chromium_fails_round_106(monkeypatch):
    """When chromium install fails, the function should call tool_error and return None."""
    # Arrange: pip present, chromium missing
    monkeypatch.setattr(scrape, "check_env", lambda: (True, False))

    # For chromium command, run_install should fail
    def fake_run_install(cmd):
        # detect playwright chromium install by presence of 'playwright' or '-m'
        if any("playwright" in str(p) for p in cmd):
            return (False, "chromium failed: network error")
        return (True, "ok")

    monkeypatch.setattr(scrape.utils, "run_install", fake_run_install)
    # Ensure urls string known
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.local/playwright", raising=False)

    io = FakeIO(confirm_return=True)

    # Act
    result = scrape.install_playwright(io)

    # Assert
    assert result is None
    assert any("chromium failed: network error" in e for e in io.errors)


def test_install_playwright_both_missing_success_round_106(monkeypatch):
    """When both pip and chromium are missing and both installs succeed, function returns True."""
    # Arrange: both missing
    monkeypatch.setattr(scrape, "check_env", lambda: (False, False))

    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda args: pip_cmd)
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.local/playwright", raising=False)

    # Both installs succeed
    def fake_run_install(cmd):
        return (True, "installed ok")

    monkeypatch.setattr(scrape.utils, "run_install", fake_run_install)

    io = FakeIO(confirm_return=True)

    # Act
    result = scrape.install_playwright(io)

    # Assert
    assert result is True
    # Should have printed instructions before installing
    assert len(io.outputs) == 1
    # No tool errors
    assert io.errors == []
