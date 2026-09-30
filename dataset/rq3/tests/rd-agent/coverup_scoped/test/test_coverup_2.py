# file: rdagent/utils/env.py:475-607
# asked: {"lines": [485, 486, 487, 488, 489, 490, 491, 492, 493, 495, 496, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 513, 514, 515, 516, 517, 518, 520, 522, 523, 524, 525, 527, 528, 530, 531, 532, 533, 534, 535, 536, 537, 538, 540, 541, 543, 544, 545, 546, 549, 550, 551, 552, 556, 557, 559, 560, 561, 563, 564, 565, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 590, 591, 592, 593, 594, 595, 596, 599, 600, 601, 602, 604, 605, 607], "branches": [[486, 487], [486, 492], [487, 488], [487, 489], [492, 493], [492, 495], [502, 503], [502, 511], [505, 506], [505, 507], [507, 508], [507, 509], [513, 0], [513, 514], [515, 513], [515, 516], [522, 523], [522, 524], [527, 528], [527, 530], [556, 557], [556, 559], [559, 560], [559, 599], [568, 569], [569, 570], [569, 571], [572, 568], [572, 573], [573, 572], [573, 574], [574, 575], [574, 581], [575, 576], [577, 578], [577, 579], [581, 572], [581, 582], [582, 583], [584, 585], [584, 586], [591, 592], [591, 594], [594, 595], [594, 604]]}
# gained: {"lines": [485, 486, 487, 488, 489, 490, 491, 492, 493, 495, 496, 498, 499, 500, 501, 502, 503, 504, 505, 507, 509, 510, 511, 513, 514, 515, 516, 520, 522, 524, 525, 527, 528, 530, 531, 532, 533, 534, 535, 536, 537, 538, 540, 541, 543, 544, 545, 546, 549, 550, 551, 552, 556, 559, 560, 561, 563, 564, 565, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 590, 591, 592, 593, 594, 595, 596, 599, 600, 601, 602, 604, 605, 607], "branches": [[486, 487], [487, 488], [487, 489], [492, 493], [492, 495], [502, 503], [502, 511], [505, 507], [507, 509], [513, 0], [513, 514], [515, 516], [522, 524], [527, 528], [556, 559], [559, 560], [559, 599], [568, 569], [569, 570], [569, 571], [572, 568], [572, 573], [573, 574], [574, 575], [575, 576], [577, 578], [577, 579], [591, 592], [594, 595]]}

import io
import types
from types import SimpleNamespace
import select
import subprocess

import pytest


def _make_fake_T(return_value):
    class DummyT:
        def __init__(self, *_):
            pass

        def r(self):
            return return_value

    return DummyT


def _make_normalize_volumes(tmp_path):
    def normalize_volumes(volumes, local_path):
        """
        Create real files under tmp_path and link paths under tmp_path/links.
        Return mapping real_path_str -> link_path_str
        """
        out = {}
        links_dir = tmp_path / "links"
        links_dir.mkdir(exist_ok=True)
        idx = 0
        for real, link in volumes.items():
            # create a real file to point to
            real_file = tmp_path / f"real_{idx}"
            real_file.write_text(f"real content {idx}")
            link_file = links_dir / f"link_{idx}"
            out[str(real_file)] = str(link_file)
            idx += 1
        return out

    return normalize_volumes


def _call_unbound_run(monkeypatch, tmp_path, *, live_output):
    # import module under test
    import rdagent.utils.env as envmod
    from rdagent.utils.env import LocalEnv

    # Prepare conf object expected by LocalEnv._run
    conf = SimpleNamespace()
    # include key containing "/sample/" to hit that branch
    conf.extra_volumes = {"/some/sample/path": "/mnt/vol", "/another": {"bind": "/mnt/dictbind"}}
    conf.bin_path = "usr/local/bin:/opt/bin"
    conf.default_entry = "echo default"
    conf.live_output = live_output

    # Monkeypatch T to return a known value for .r()
    cache_target = str(tmp_path / "cache_target")
    (tmp_path / "cache_target").write_text("cache")
    monkeypatch.setattr(envmod, "T", _make_fake_T(cache_target))

    # Monkeypatch normalize_volumes so symlink paths are under tmp_path and predictable
    norm = _make_normalize_volumes(tmp_path)
    monkeypatch.setattr(envmod, "normalize_volumes", norm)

    # Prepare fake subprocess.Popen implementations depending on live_output
    if not live_output:

        class FakeStdIO(io.StringIO):
            def fileno(self):
                # provide a fileno though not used in this branch
                return 7

        class FakeProc:
            def __init__(self, *args, **kwargs):
                self.stdout = FakeStdIO("out\n")
                self.stderr = FakeStdIO("err\n")
                self.returncode = 42

            def communicate(self):
                return "final out", "final err"

            def poll(self):
                return self.returncode

        monkeypatch.setattr(envmod.subprocess, "Popen", FakeProc)
    else:
        # live_output True
        class FakeStream:
            def __init__(self, lines, fd):
                self._lines = list(lines)
                self._fd = fd

            def fileno(self):
                return self._fd

            def readline(self):
                if not self._lines:
                    return ""
                return self._lines.pop(0)

            def read(self):
                # not used
                return "".join(self._lines)

        class FakeProc:
            def __init__(self, *args, **kwargs):
                # stdout will have one line, stderr empty
                self.stdout = FakeStream(["line1\n"], 3)
                self.stderr = FakeStream([], 4)
                self._poll_calls = 0
                self.returncode = 0

            def poll(self):
                # return None first time to enter loop, then 0 to break
                self._poll_calls += 1
                if self._poll_calls == 1:
                    return None
                return self.returncode

            def communicate(self):
                return "remaining_out", "remaining_err"

        # Provide a fake poller to control events
        class FakePoller:
            def __init__(self):
                self.reg = {}

            def register(self, fd, eventmask):
                self.reg[fd] = eventmask

            def poll(self, timeout=None):
                # On first call, return an event for stdout fd (3). After that, return empty.
                if not hasattr(self, "_called"):
                    self._called = True
                    return [(3, select.POLLIN)]
                return []

        monkeypatch.setattr(envmod.subprocess, "Popen", FakeProc)
        monkeypatch.setattr(envmod.select, "poll", lambda: FakePoller())

    # Build a fake 'self' and call the unbound method
    self_obj = SimpleNamespace(conf=conf)

    # Prepare running_extra_volume to test merging into volumes
    running_extra_volume = {str(tmp_path / "running_real"): str(tmp_path / "running_link")}

    # Call the unbound LocalEnv._run with our fake self
    result = LocalEnv._run(self_obj, entry=None, local_path=str(tmp_path), env={"PATH": "/usr/bin"}, running_extra_volume=running_extra_volume)

    return result, tmp_path


def test_localenv_run_non_live_output(monkeypatch, tmp_path):
    result, tmp_path = _call_unbound_run(monkeypatch, tmp_path, live_output=False)
    combined_output, return_code = result
    # Expect the combined output to be the communicate() return concatenated
    assert combined_output == "final outfinal err"
    assert return_code == 42

    # Ensure that no link files remain in the links directory (symlink cleanup happened)
    links_dir = tmp_path / "links"
    # Normalize function created link files as link_0, link_1, etc.
    if links_dir.exists():
        # should be empty
        remaining = list(links_dir.iterdir())
        assert remaining == []


def test_localenv_run_live_output(monkeypatch, tmp_path):
    result, tmp_path = _call_unbound_run(monkeypatch, tmp_path, live_output=True)
    combined_output, return_code = result
    # Expect to have the line from stdout plus remaining communicate output
    assert combined_output == "line1\nremaining_outremaining_err"
    assert return_code == 0

    # Ensure that no link files remain in the links directory (symlink cleanup happened)
    links_dir = tmp_path / "links"
    if links_dir.exists():
        remaining = list(links_dir.iterdir())
        assert remaining == []
