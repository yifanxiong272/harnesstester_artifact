# file: aider/io.py:1054-1086
# asked: {"lines": [1056, 1058, 1060, 1062, 1063, 1065, 1066, 1068, 1070, 1071, 1072, 1073, 1074, 1075, 1076, 1077, 1079, 1080, 1082, 1086], "branches": [[1060, 1062], [1060, 1068], [1062, 1063], [1062, 1065], [1068, 1070], [1068, 1077], [1070, 1071], [1070, 1076], [1071, 1070], [1071, 1072], [1072, 1073], [1072, 1074], [1074, 1070], [1074, 1075], [1077, 1079], [1077, 1086]]}
# gained: {"lines": [1056, 1058, 1060, 1062, 1063, 1065, 1066, 1068, 1070, 1071, 1072, 1073, 1074, 1075, 1076, 1077, 1079, 1080, 1082, 1086], "branches": [[1060, 1062], [1060, 1068], [1062, 1063], [1062, 1065], [1068, 1070], [1068, 1077], [1070, 1071], [1070, 1076], [1071, 1070], [1071, 1072], [1072, 1073], [1072, 1074], [1074, 1075], [1077, 1079], [1077, 1086]]}

import importlib
import platform
import shutil
import pytest


def _get_io_module():
    return importlib.import_module("aider.io")


def _make_io(mod):
    return mod.InputOutput()


def _set_message(mod, msg, monkeypatch):
    # Set NOTIFICATION_MESSAGE in the module under test
    monkeypatch.setattr(mod, "NOTIFICATION_MESSAGE", msg, raising=False)


def test_darwin_with_terminal_notifier(monkeypatch):
    mod = _get_io_module()
    _set_message(mod, "MSG1", monkeypatch)

    # Patch platform.system and shutil.which
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/terminal-notifier" if cmd == "terminal-notifier" else None)

    io = _make_io(mod)
    result = io.get_default_notification_command()
    assert result == "terminal-notifier -title 'Aider' -message 'MSG1'"


def test_darwin_without_terminal_notifier_uses_osascript(monkeypatch):
    mod = _get_io_module()
    _set_message(mod, "HelloDarwin", monkeypatch)

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    # No terminal-notifier available
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = _make_io(mod)
    result = io.get_default_notification_command()
    expected = "osascript -e 'display notification \"HelloDarwin\" with title \"Aider\"'"
    assert result == expected


def test_linux_notify_send_and_zenity_branches(monkeypatch):
    mod = _get_io_module()
    _set_message(mod, "LMSG", monkeypatch)

    # Case 1: notify-send exists
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/notify-send" if cmd == "notify-send" else None)
    io = _make_io(mod)
    res = io.get_default_notification_command()
    assert res == "notify-send 'Aider' 'LMSG'"

    # Case 2: notify-send missing, zenity exists
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/zenity" if cmd == "zenity" else None)
    res2 = io.get_default_notification_command()
    assert res2 == "zenity --notification --text='LMSG'"

    # Case 3: neither exists
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    res3 = io.get_default_notification_command()
    assert res3 is None


def test_windows_returns_powershell_string(monkeypatch):
    mod = _get_io_module()
    _set_message(mod, "WINMSG", monkeypatch)

    monkeypatch.setattr(platform, "system", lambda: "Windows")
    # shutil.which is not used for Windows branch but patch defensively
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = _make_io(mod)
    res = io.get_default_notification_command()
    assert isinstance(res, str)
    # Check important substrings are present
    assert "powershell -command" in res
    assert "MessageBox" in res or "MessageBox" in res  # ensure the MessageBox invocation is present
    assert "WINMSG" in res
    assert "Aider" in res


def test_unknown_system_returns_none(monkeypatch):
    mod = _get_io_module()
    _set_message(mod, "XYZ", monkeypatch)

    monkeypatch.setattr(platform, "system", lambda: "Plan9")
    monkeypatch.setattr(shutil, "which", lambda cmd: None)

    io = _make_io(mod)
    assert io.get_default_notification_command() is None
