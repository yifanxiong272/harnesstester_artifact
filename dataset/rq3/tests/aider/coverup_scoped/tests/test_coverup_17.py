# file: aider/io.py:1054-1086
# asked: {"lines": [1056, 1058, 1060, 1062, 1063, 1065, 1066, 1068, 1070, 1071, 1072, 1073, 1074, 1075, 1076, 1077, 1079, 1080, 1082, 1086], "branches": [[1060, 1062], [1060, 1068], [1062, 1063], [1062, 1065], [1068, 1070], [1068, 1077], [1070, 1071], [1070, 1076], [1071, 1070], [1071, 1072], [1072, 1073], [1072, 1074], [1074, 1070], [1074, 1075], [1077, 1079], [1077, 1086]]}
# gained: {"lines": [1056, 1058, 1060, 1062, 1063, 1065, 1066, 1068, 1070, 1071, 1072, 1073, 1074, 1075, 1076, 1077, 1079, 1080, 1082, 1086], "branches": [[1060, 1062], [1060, 1068], [1062, 1063], [1062, 1065], [1068, 1070], [1068, 1077], [1070, 1071], [1070, 1076], [1071, 1070], [1071, 1072], [1072, 1073], [1072, 1074], [1074, 1075], [1077, 1079], [1077, 1086]]}

import platform
import shutil

import pytest

from aider.io import InputOutput, NOTIFICATION_MESSAGE


def test_darwin_with_terminal_notifier(monkeypatch):
    # Simulate macOS with terminal-notifier available
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/terminal-notifier" if cmd == "terminal-notifier" else None)

    io = InputOutput()
    result = io.get_default_notification_command()

    expected = f"terminal-notifier -title 'Aider' -message '{NOTIFICATION_MESSAGE}'"
    assert result == expected


def test_darwin_without_terminal_notifier(monkeypatch):
    # Simulate macOS without terminal-notifier -> fallback to osascript
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = InputOutput()
    result = io.get_default_notification_command()

    expected = f"osascript -e 'display notification \"{NOTIFICATION_MESSAGE}\" with title \"Aider\"'"
    assert result == expected


def test_linux_with_notify_send(monkeypatch):
    # Simulate Linux with notify-send available
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/notify-send" if cmd == "notify-send" else None)

    io = InputOutput()
    result = io.get_default_notification_command()

    expected = f"notify-send 'Aider' '{NOTIFICATION_MESSAGE}'"
    assert result == expected


def test_linux_with_zenity(monkeypatch):
    # Simulate Linux with zenity available but no notify-send
    def fake_which(cmd):
        if cmd == "notify-send":
            return None
        if cmd == "zenity":
            return "/usr/bin/zenity"
        return None

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shutil, "which", fake_which)

    io = InputOutput()
    result = io.get_default_notification_command()

    expected = f"zenity --notification --text='{NOTIFICATION_MESSAGE}'"
    assert result == expected


def test_linux_without_tools(monkeypatch):
    # Simulate Linux with no known notification tools
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = InputOutput()
    result = io.get_default_notification_command()

    assert result is None


def test_windows_notification_command(monkeypatch):
    # Simulate Windows system
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    # which is irrelevant on Windows for this function, but ensure it exists
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = InputOutput()
    result = io.get_default_notification_command()

    expected = (
        "powershell -command "
        f"\"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
        f"[System.Windows.Forms.MessageBox]::Show('{NOTIFICATION_MESSAGE}', 'Aider')\""
    )
    # Normalize spaces because the implementation concatenates literals; exact spacing should match
    assert result == expected


def test_unknown_system_returns_none(monkeypatch):
    # Simulate an unknown/unsupported system
    monkeypatch.setattr(platform, "system", lambda: "Solaris")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = InputOutput()
    result = io.get_default_notification_command()

    assert result is None
