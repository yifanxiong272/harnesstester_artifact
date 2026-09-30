import io
import os
from types import SimpleNamespace
from pathlib import Path
import pytest

import rdagent.utils.env as env_mod


class _FakeConsole:
    def print(self, *args, **kwargs):
        # no-op to avoid noisy output during tests
        return None


def _make_fake_proc_no_live(out_text="OUT", err_text="ERR", returncode=42):
    class FakeProc:
        def __init__(self):
            self.stdout = io.StringIO("")
            self.stderr = io.StringIO("")
            self.returncode = returncode

        def communicate(self):
            return (out_text, err_text)

        def poll(self):
            return 0

    return FakeProc()


def _make_fake_proc_live(remaining_out="REM_OUT", remaining_err="REM_ERR", returncode=0):
    class StdLike:
        def __init__(self, fd):
            self._fd = fd

        def fileno(self):
            # return small integers to register with poll() - valid values are fine as poll doesn't actually read them here
            return self._fd

        def readline(self):
            # return empty to simulate no incremental output
            return ""

    class FakeProc:
        def __init__(self):
            self.stdout = StdLike(1)
            self.stderr = StdLike(2)
            self.returncode = returncode

        def communicate(self):
            return (remaining_out, remaining_err)

        def poll(self):
            # return non-None immediately so the event loop breaks and the code goes to .communicate()
            return 1

    return FakeProc()


def test_localenv_run_no_live_output_round_008(monkeypatch, tmp_path):
    """
    Exercise the non-live_output path of LocalEnv._run. This mocks subprocess.Popen to avoid spawning a real process and
    verifies the returned combined output and return code. It also verifies that symlink cleanup occurs (links removed).
    """
    # Prepare a minimal conf object expected by LocalEnv
    conf = SimpleNamespace(
        extra_volumes=None,
        bin_path="/bin1:/bin2",
        default_entry="echo hi",
        live_output=False,
    )

    # Instantiate LocalEnv using the real class (it relies only on .conf attribute for this method)
    env = env_mod.LocalEnv(conf)

    # Prepare a simple running_extra_volume mapping (real -> link)
    real = tmp_path / "real_data"
    real.write_text("some data")
    link = tmp_path / "link_location" / "linkfile"

    running_extra_volume = {str(real): str(link)}

    # Patch Console to avoid prints
    monkeypatch.setattr(env_mod, "Console", _FakeConsole)

    # Patch subprocess.Popen to return a fake process that will be used by the non-live branch
    def fake_popen(*args, **kwargs):
        return _make_fake_proc_no_live(out_text="OUT", err_text="ERR", returncode=42)

    monkeypatch.setattr(env_mod.subprocess, "Popen", fake_popen)

    # Run
    combined_output, rc = env._run(entry="/bin/true", local_path=str(tmp_path), env={"X": "1"}, running_extra_volume=running_extra_volume)

    # Oracle: combined output should be concatenation of stdout+stderr from communicate and rc should match
    assert combined_output == "OUTERR"
    assert rc == 42

    # Symlink created during the run should have been removed by the context manager finalizer
    # Since link parent might have been created, verify link no longer exists
    assert not link.exists()


def test_localenv_run_live_output_round_008(monkeypatch, tmp_path):
    """
    Exercise the live_output path of LocalEnv._run. This patches T to return a stable cache path, sets up extra_volumes
    so the cache path branch is executed, and patches subprocess.Popen to a fake that triggers the 'remaining output' handling.
    """
    # Create a conf where extra_volumes is present to hit that branch and live_output is True
    # Use paths that include '/sample/' substring in the extra volume key to trigger the sample cache path branch
    sample_key = "/some/sample/path"
    bind_target = tmp_path / "bind_target"
    bind_target.write_text("bind target content")

    conf = SimpleNamespace(
        extra_volumes={sample_key: {"bind": str(bind_target)}},
        bin_path="/binA:/binB",
        default_entry="/bin/echo",
        live_output=True,
    )

    # Ensure T().r() returns a path under tmp_path so the symlink target exists
    class _FakeT:
        def __init__(self, *args, **kwargs):
            pass

        def r(self):
            p = tmp_path / "cache_real"
            p.write_text("cache content")
            return str(p)

    monkeypatch.setattr(env_mod, "T", _FakeT)

    # Patch Console to avoid prints
    monkeypatch.setattr(env_mod, "Console", _FakeConsole)

    # Patch subprocess.Popen for the live_output scenario. The fake process will cause the polling loop to exit quickly
    def fake_popen(*args, **kwargs):
        return _make_fake_proc_live(remaining_out="REM_OUT", remaining_err="REM_ERR", returncode=0)

    monkeypatch.setattr(env_mod.subprocess, "Popen", fake_popen)

    env = env_mod.LocalEnv(conf)

    # running_extra_volume to add at least one more symlink entry
    real2 = tmp_path / "real2"
    real2.write_text("r2 content")
    link2 = tmp_path / "link2"
    running_extra_volume = {str(real2): str(link2)}

    combined_output, rc = env._run(entry="/bin/echo hello", local_path=str(tmp_path), env={"Y": "2"}, running_extra_volume=running_extra_volume)

    # Oracle: combined output should equal remaining output + remaining error and return code should be 0
    assert combined_output == "REM_OUTREM_ERR"
    assert rc == 0

    # Links created by the context manager should be removed afterwards
    assert not link2.exists()
