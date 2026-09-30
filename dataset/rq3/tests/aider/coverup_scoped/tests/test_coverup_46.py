# file: aider/scrape.py:40-76
# asked: {"lines": [43, 51, 63, 66, 67, 68, 69, 73, 74], "branches": [[42, 43], [50, 51], [52, 55], [62, 63], [65, 66], [67, 68], [67, 71], [72, 73]]}
# gained: {"lines": [43, 51, 63, 66, 67, 68, 69, 73, 74], "branches": [[42, 43], [50, 51], [52, 55], [62, 63], [65, 66], [67, 68], [67, 71], [72, 73]]}

import sys
import types
import pytest

import aider.scrape as scrape


class DummyIO:
    def __init__(self, confirm_return=True):
        self.outputs = []
        self.errors = []
        self.confirm_return = confirm_return
        self.confirm_calls = []

    def tool_output(self, text):
        self.outputs.append(text)

    def tool_error(self, text):
        self.errors.append(text)

    def confirm_ask(self, prompt, default="y"):
        self.confirm_calls.append((prompt, default))
        return self.confirm_return


def test_install_playwright_already_installed(monkeypatch):
    # Arrange: simulate environment already having pip and chromium
    monkeypatch.setattr(scrape, "check_env", lambda: (True, True))

    io = DummyIO()
    # Act
    result = scrape.install_playwright(io)
    # Assert
    assert result is True
    # No outputs or errors should have been produced
    assert io.outputs == []
    assert io.errors == []


def test_install_playwright_show_cmds_and_decline(monkeypatch):
    # Arrange: neither pip nor chromium installed; user declines installation
    monkeypatch.setattr(scrape, "check_env", lambda: (False, False))
    # Make get_pip_install deterministic
    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda pkg: pip_cmd)
    # Make sure URL is known
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.com/playwright")
    io = DummyIO(confirm_return=False)

    # Act
    result = scrape.install_playwright(io)

    # Assert: Because user declined, function returns None
    assert result is None
    # tool_output must have been called once with both pip and playwright install commands and the URL
    assert len(io.outputs) == 1
    out = io.outputs[0]
    # pip command present
    assert " ".join(pip_cmd) in out
    # playwright install present (chromium command)
    assert "playwright install --with-deps chromium" in out
    # URL present
    assert "https://example.com/playwright" in out
    # confirm_ask called
    assert io.confirm_calls and io.confirm_calls[0][0].startswith("Install playwright?")


def test_install_playwright_pip_install_failure(monkeypatch):
    # Arrange: pip missing, chromium already present -> only pip install attempted
    monkeypatch.setattr(scrape, "check_env", lambda: (False, True))
    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda pkg: pip_cmd)
    # Ensure URL doesn't interfere
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.com/playwright")

    # Prepare run_install to fail for pip
    calls = []

    def fake_run_install(cmd):
        calls.append(list(cmd))
        if cmd == pip_cmd:
            return False, "pip failed"
        return True, "ok"

    monkeypatch.setattr(scrape.utils, "run_install", fake_run_install)

    io = DummyIO(confirm_return=True)

    # Act
    result = scrape.install_playwright(io)

    # Assert: pip install attempted and failed, error reported, returns None
    assert result is None
    assert calls and calls[0] == pip_cmd
    assert io.errors == ["pip failed"]


def test_install_playwright_chromium_install_failure(monkeypatch):
    # Arrange: pip present, chromium missing -> only chromium install attempted
    monkeypatch.setattr(scrape, "check_env", lambda: (True, False))
    # get_pip_install still called but pip is present so run_install for pip should be skipped
    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda pkg: pip_cmd)
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.com/playwright")

    calls = []

    def fake_run_install(cmd):
        calls.append(list(cmd))
        # Expect chromium install command (starts with sys.executable)
        if cmd[1:] == ["-m", "playwright", "install", "--with-deps", "chromium"]:
            return False, "chromium failed"
        return True, "ok"

    monkeypatch.setattr(scrape.utils, "run_install", fake_run_install)

    io = DummyIO(confirm_return=True)

    # Act
    result = scrape.install_playwright(io)

    # Assert: chromium install attempted and failed, error reported, returns None
    assert result is None
    # There should be exactly one run_install call for chromium
    assert any("playwright" in " ".join(c) for c in calls)
    assert io.errors == ["chromium failed"]


def test_install_playwright_successful_installs(monkeypatch):
    # Arrange: neither installed, user agrees, both installs succeed
    monkeypatch.setattr(scrape, "check_env", lambda: (False, False))
    pip_cmd = ["pip", "install", "aider-chat[playwright]"]
    monkeypatch.setattr(scrape.utils, "get_pip_install", lambda pkg: pip_cmd)
    monkeypatch.setattr(scrape.urls, "enable_playwright", "https://example.com/playwright")

    calls = []

    def fake_run_install(cmd):
        calls.append(list(cmd))
        return True, "ok"

    monkeypatch.setattr(scrape.utils, "run_install", fake_run_install)

    io = DummyIO(confirm_return=True)

    # Act
    result = scrape.install_playwright(io)

    # Assert: both run_install calls executed and function returns True
    assert result is True
    # Expect two installs: pip and chromium
    assert len(calls) == 2
    # First call equals pip_cmd
    assert calls[0] == pip_cmd
    # Second call starts with sys.executable and contains playwright
    assert calls[1][0] == sys.executable
    assert "playwright" in " ".join(calls[1])
    # No errors
    assert io.errors == []
