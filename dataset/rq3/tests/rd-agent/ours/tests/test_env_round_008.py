import importlib
import types
from types import SimpleNamespace
import pytest


env_mod = importlib.import_module("rdagent.utils.env")


class _DummyConsole:
    def __init__(self):
        self.calls = []

    def print(self, *args, **kwargs):
        # record a simple tuple of what was printed for deterministic assertions
        self.calls.append((args, kwargs))


def _make_conf(extra_volumes=None, bin_path="/bin:/usr/bin", default_entry="echo hi", live_output=False):
    return SimpleNamespace(extra_volumes=extra_volumes, bin_path=bin_path, default_entry=default_entry, live_output=live_output)


def test_non_live_output_and_symlink_cleanup_round_008(tmp_path, monkeypatch):
    """
    Exercise the branch where extra_volumes is present, normalize_volumes is used,
    and live_output is False (communicate path). Verify combined output & return code
    and that console print was invoked for out/err.
    """
    # Prepare a dummy console to capture prints
    dummy_console = _DummyConsole()
    monkeypatch.setattr(env_mod, "Console", lambda: dummy_console)

    # Ensure normalize_volumes returns the volumes mapping unchanged so the symlink context is exercised
    monkeypatch.setattr(env_mod, "normalize_volumes", lambda volumes, local_path: volumes)

    # Provide a T(...) mock where .r() returns a path inside tmp_path (safe, deterministic)
    class DummyT:
        def __init__(self, *args, **kwargs):
            pass

        def r(self):
            return str(tmp_path / "cached_value")

    monkeypatch.setattr(env_mod, "T", DummyT)

    # Fake subprocess.Popen for the non-live branch
    class DummyStream:
        def fileno(self):
            return 3

        def readline(self):
            return ""  # not used in non-live branch

    class FakePopenNonLive:
        def __init__(self, *args, **kwargs):
            self.stdout = DummyStream()
            self.stderr = DummyStream()
            # communicate will be used in non-live branch
            self.returncode = 5

        def communicate(self):
            return ("OUT_CONTENT", "ERR_CONTENT")

    monkeypatch.setattr(env_mod.subprocess, "Popen", FakePopenNonLive)

    # Prepare conf.extra_volumes such that the keys include '/sample/' to exercise that cache_path branch
    host_sample = str(tmp_path / "some" / "sample" / "hostdir")
    container_link = str(tmp_path / "some" / "linkdir")
    extra_volumes = {host_sample: container_link}

    self_obj = SimpleNamespace(conf=_make_conf(extra_volumes=extra_volumes, live_output=False))

    # running_extra_volume: map a host real path to another link path (these will be processed by _symlink_ctx)
    running_extra_volume = {str(tmp_path / "realdir"): str(tmp_path / "linkdir2")}

    combined_output, rc = env_mod.LocalEnv._run(self_obj, entry="echo hi", local_path=str(tmp_path), env={"PATH": "/my/path"}, running_extra_volume=running_extra_volume)

    # Assert returned values come from FakePopenNonLive.communicate() and returncode is propagated
    assert combined_output == "OUT_CONTENTERR_CONTENT"
    assert rc == 5

    # Console.print should have been called for out and err (two calls recorded)
    # In non-live branch the code calls Console().print(out, end="", markup=False) and Console().print(err, ...)
    # We check that at least two print calls were made and their first positional arg includes the out/err content
    assert len(dummy_console.calls) >= 2
    first_args, _ = dummy_console.calls[0]
    second_args, _ = dummy_console.calls[1]
    assert "OUT_CONTENT" in (first_args[0] if first_args else "")
    assert "ERR_CONTENT" in (second_args[0] if second_args else "")


def test_live_output_polling_and_combined_capture_round_008(monkeypatch):
    """
    Simulate a process with live_output True. The test patches select.poll to control events,
    and uses streams whose readline returns content then empty string. Verify loop reads both stdout and stderr
    and combined_output contains both pieces.
    """
    dummy_console = _DummyConsole()
    monkeypatch.setattr(env_mod, "Console", lambda: dummy_console)
    monkeypatch.setattr(env_mod, "normalize_volumes", lambda volumes, local_path: volumes)

    # Build a fake Popen that simulates polling and streaming
    class FakeStream:
        def __init__(self, lines):
            self._lines = list(lines)

        def fileno(self):
            # return a unique integer to match poll events
            return id(self) & 0xFFFF

        def readline(self):
            # Return next line or empty string to signal EOF
            return self._lines.pop(0) if self._lines else ""

    class FakePopenLive:
        def __init__(self, *args, **kwargs):
            self.stdout = FakeStream(["out_line1\n"])
            self.stderr = FakeStream(["err_line1\n"])
            self._poll_calls = 0
            self.returncode = 0

        def poll(self):
            # First call: process still running (None), second call: finished (0)
            self._poll_calls += 1
            return None if self._poll_calls == 1 else 0

        def communicate(self):
            # No remaining output
            return ("", "")

    fake_proc = FakePopenLive()

    # Replace subprocess.Popen to return our fake instance
    def fake_popen(*args, **kwargs):
        return fake_proc

    monkeypatch.setattr(env_mod.subprocess, "Popen", fake_popen)

    # Fake poller: yields a single batch of events corresponding to stdout and stderr filenos
    class FakePoll:
        def __init__(self):
            self._returned = False

        def register(self, fd, eventmask):
            # no-op
            pass

        def poll(self, timeout):
            if not self._returned:
                self._returned = True
                return [(fake_proc.stdout.fileno(), env_mod.select.POLLIN), (fake_proc.stderr.fileno(), env_mod.select.POLLIN)]
            return []

    monkeypatch.setattr(env_mod.select, "poll", lambda: FakePoll())

    # Prepare self object with no extra volumes (exercises empty-volumes path)
    self_obj = SimpleNamespace(conf=_make_conf(extra_volumes=None, live_output=True))

    combined_output, rc = env_mod.LocalEnv._run(self_obj, entry="echo hi", local_path="/tmp", env={}, running_extra_volume={})

    assert rc == 0
    # combined_output should include the two streamed lines we provided (with their newlines)
    assert "out_line1\n" in combined_output
    assert "err_line1\n" in combined_output

    # Console should have printed those lines (strip called in code), so check recorded calls contain the text
    flattened = "".join(a[0][0] if a[0] else "" for a in dummy_console.calls)
    assert "out_line1" in flattened
    assert "err_line1" in flattened


def test_subprocess_without_pipes_raises_runtime_error_round_008(monkeypatch):
    """
    If subprocess.Popen returns an object with stdout or stderr set to None, _run should raise RuntimeError.
    """
    class BadPopen:
        def __init__(self, *args, **kwargs):
            self.stdout = None
            self.stderr = None
            self.returncode = 0

    monkeypatch.setattr(env_mod.subprocess, "Popen", BadPopen)

    self_obj = SimpleNamespace(conf=_make_conf(extra_volumes=None, live_output=False))

    with pytest.raises(RuntimeError, match="The subprocess did not correctly create stdout/stderr pipes"):
        env_mod.LocalEnv._run(self_obj, entry="echo hi", local_path="/tmp", env={}, running_extra_volume={})
