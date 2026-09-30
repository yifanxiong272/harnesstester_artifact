import subprocess
import pytest

from gpt_researcher.llm_provider.generic import base


def test_no_install_round_117(monkeypatch):
    """When the package is already installed (find_spec truthy), nothing is invoked."""
    # make find_spec return a truthy value -> skip installation
    monkeypatch.setattr(base.importlib.util, "find_spec", lambda pkg: object())

    # If subprocess.check_call is called unexpectedly, fail the test.
    def _fail(*a, **k):
        raise AssertionError("subprocess.check_call should not have been called")

    monkeypatch.setattr(base.subprocess, "check_call", _fail)

    # Should not raise
    base._check_pkg("already_installed_pkg")


def test_install_success_round_117(monkeypatch, capsys):
    """When find_spec is falsy and pip install succeeds, import_module is attempted and prints occur."""
    # Simulate package not present
    monkeypatch.setattr(base.importlib.util, "find_spec", lambda pkg: None)

    # Patch colorama init to avoid side effects
    monkeypatch.setattr(base, "init", lambda **kw: None)

    calls = {"check_call": None, "imported": None}

    def fake_check_call(cmd):
        # record that pip was invoked and with the expected package style
        calls["check_call"] = list(cmd)
        return 0

    def fake_import_module(pkg):
        calls["imported"] = pkg
        return None

    monkeypatch.setattr(base.subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(base.importlib, "import_module", fake_import_module)

    # Use an underscore to verify kebab conversion
    base._check_pkg("my_pkg")

    # verify pip command included the kebab-case package
    assert calls["check_call"] is not None, "pip install was not attempted"
    assert "my-pkg" in " ".join(calls["check_call"])

    # verify import_module called with original pkg name
    assert calls["imported"] == "my_pkg"

    captured = capsys.readouterr()
    assert "Installing my-pkg" in captured.out
    assert "Successfully installed my-pkg" in captured.out


def test_install_fail_round_117(monkeypatch, capsys):
    """When pip install fails (CalledProcessError), ImportError is raised with guidance message."""
    monkeypatch.setattr(base.importlib.util, "find_spec", lambda pkg: None)
    monkeypatch.setattr(base, "init", lambda **kw: None)

    # Ensure import_module would not be reached; if it is, fail the test
    def _import_fail(*a, **k):
        raise AssertionError("import_module should not be called on failed install")

    monkeypatch.setattr(base.importlib, "import_module", _import_fail)

    def raising_check_call(cmd):
        # Simulate pip failing
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(base.subprocess, "check_call", raising_check_call)

    with pytest.raises(ImportError) as excinfo:
        base._check_pkg("failing_pkg")

    msg = str(excinfo.value)
    # The message should instruct the user to pip install the kebab-case package
    assert "Failed to install failing-pkg" in msg or "pip install -U failing-pkg" in msg

    # The first print (Installing ...) should have occurred before the failure
    captured = capsys.readouterr()
    assert "Installing failing-pkg" in captured.out
