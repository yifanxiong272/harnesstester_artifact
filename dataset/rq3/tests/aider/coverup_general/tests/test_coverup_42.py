# file: aider/versioncheck.py:29-61
# asked: {"lines": [34, 35, 37, 39, 40, 41, 42, 44, 46, 47, 49, 50, 51, 52, 53, 54, 57, 58, 59, 61], "branches": [[34, 35], [34, 37], [40, 41], [40, 49], [57, 58], [57, 61]]}
# gained: {"lines": [34, 35, 37, 39, 40, 41, 42, 44, 46, 47, 49, 50, 51, 52, 53, 54, 57, 58, 59, 61], "branches": [[34, 35], [34, 37], [40, 41], [40, 49], [57, 58], [57, 61]]}

import sys
import os
import pytest

from aider import versioncheck


class DummyIO:
    def __init__(self):
        self.warnings = []
        self.outputs = []

    def tool_warning(self, text):
        self.warnings.append(text)

    def tool_output(self, text):
        self.outputs.append(text)


def test_install_upgrade_uses_docker_image_and_shows_latest_version(monkeypatch):
    # Arrange
    monkeypatch.setenv("AIDER_DOCKER_IMAGE", "my/image:latest")
    io = DummyIO()

    # Act
    result = versioncheck.install_upgrade(io, latest_version="1.2.3")

    # Assert
    assert result is True
    assert len(io.warnings) == 1
    warning_text = io.warnings[0]
    assert "Newer aider version v1.2.3 is available." in warning_text
    assert "docker pull my/image:latest" in warning_text

    # Cleanup
    monkeypatch.delenv("AIDER_DOCKER_IMAGE", raising=False)


def test_install_upgrade_calls_check_pip_and_exits_on_success(monkeypatch):
    # Arrange
    monkeypatch.delenv("AIDER_DOCKER_IMAGE", raising=False)
    io = DummyIO()

    called = {}

    def fake_check(io_arg, none_arg, new_ver_text_arg, pkg_list_arg, self_update=False):
        # capture arguments for assertions, then return True to simulate success
        called['io_arg'] = io_arg
        called['none_arg'] = none_arg
        called['new_ver_text_arg'] = new_ver_text_arg
        called['pkg_list_arg'] = list(pkg_list_arg)
        called['self_update'] = self_update
        return True

    monkeypatch.setattr(
        "aider.versioncheck.utils.check_pip_install_extra", fake_check
    )

    def fake_exit():
        raise SystemExit(0)

    monkeypatch.setattr(sys, "exit", fake_exit)

    # Act / Assert: should raise SystemExit due to successful install triggering sys.exit()
    with pytest.raises(SystemExit):
        versioncheck.install_upgrade(io, latest_version="2.0.0")

    # Further assertions after exit raised
    assert io.outputs == ["Re-run aider to use new version."]
    # check the parameters passed to check_pip_install_extra
    assert called["none_arg"] is None
    assert called["new_ver_text_arg"] == "Newer aider version v2.0.0 is available."
    assert called["pkg_list_arg"] == ["aider-chat"]
    assert called["self_update"] is True


def test_install_upgrade_returns_none_when_check_pip_fails(monkeypatch):
    # Arrange: ensure no docker image
    monkeypatch.delenv("AIDER_DOCKER_IMAGE", raising=False)
    io = DummyIO()

    called = {}

    def fake_check(io_arg, none_arg, new_ver_text_arg, pkg_list_arg, self_update=False):
        called['new_ver_text_arg'] = new_ver_text_arg
        called['pkg_list_arg'] = list(pkg_list_arg)
        called['self_update'] = self_update
        return False

    monkeypatch.setattr(
        "aider.versioncheck.utils.check_pip_install_extra", fake_check
    )

    # Act
    result = versioncheck.install_upgrade(io, latest_version=None)

    # Assert
    assert result is None
    assert io.outputs == []
    # new_ver_text should be the fallback when latest_version is None
    assert called["new_ver_text_arg"] == "Install latest version of aider?"
    assert called["pkg_list_arg"] == ["aider-chat"]
    assert called["self_update"] is True
