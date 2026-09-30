import platform
import aider.io as io


def _make_instance_without_init():
    # Avoid running potentially heavy __init__; method does not use self state.
    return object.__new__(io.InputOutput)


def test_darwin_terminal_round_041(monkeypatch):
    # Darwin with terminal-notifier present -> terminal-notifier branch
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(io.shutil, "which", lambda cmd: True)
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "HelloNotify")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert isinstance(res, str)
    assert "terminal-notifier" in res
    assert "HelloNotify" in res


def test_darwin_osascript_round_041(monkeypatch):
    # Darwin when terminal-notifier is absent -> osascript fallback
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(io.shutil, "which", lambda cmd: False)
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "OSAScriptMsg")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert isinstance(res, str)
    assert "osascript" in res
    assert "display notification" in res
    assert "OSAScriptMsg" in res


def test_linux_notify_send_round_041(monkeypatch):
    # Linux: notify-send found first -> notify-send branch
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    def which_notify(cmd):
        return cmd == "notify-send"

    monkeypatch.setattr(io.shutil, "which", which_notify)
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "LinMsg")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert isinstance(res, str)
    assert "notify-send" in res
    assert "LinMsg" in res


def test_linux_zenity_round_041(monkeypatch):
    # Linux: notify-send absent but zenity present -> zenity branch
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    def which_zenity(cmd):
        # simulate notify-send absent, zenity present
        return cmd == "zenity"

    monkeypatch.setattr(io.shutil, "which", which_zenity)
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "ZenMsg")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert isinstance(res, str)
    assert "zenity" in res
    assert "ZenMsg" in res


def test_linux_none_round_041(monkeypatch):
    # Linux: no known notification tools -> returns None
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(io.shutil, "which", lambda cmd: False)
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "NoTool")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert res is None


def test_windows_powershell_round_041(monkeypatch):
    # Windows -> powershell formatted command including the message
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "WinMsg")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert isinstance(res, str)
    assert "powershell" in res.lower()
    assert "WinMsg" in res


def test_unknown_system_round_041(monkeypatch):
    # Unknown system should return None
    monkeypatch.setattr(platform, "system", lambda: "BeOS")
    monkeypatch.setattr(io.shutil, "which", lambda cmd: True)
    monkeypatch.setattr(io, "NOTIFICATION_MESSAGE", "X")

    inst = _make_instance_without_init()
    res = io.InputOutput.get_default_notification_command(inst)

    assert res is None
