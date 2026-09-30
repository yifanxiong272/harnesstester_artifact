import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.run_cmd')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure run_cmd takes the pexpect path and returns captured output."""
        # Create a fake pexpect.spawn that simulates a child process producing bytes
        def fake_spawn(*args, **kwargs):
            class FakeChild:
                def __init__(self):
                    # simulate a successful exit status
                    self.exitstatus = 0

                def interact(self, output_filter=None, *a, **k):
                    # simulate interactive output; output_filter is expected to accept bytes
                    if output_filter:
                        output_filter(b"mocked-pexpect-output")
                        # simulate more output
                        output_filter(b"\nsecond-line")

                def close(self):
                    # nothing to do for the fake
                    pass

            return FakeChild()

        # Save originals to restore later
        old_stdin = sys.stdin
        old_platform_system = platform.system
        old_pexpect_spawn = getattr(pexpect, "spawn", None)

        # Replace sys.stdin with an object whose isatty() returns True
        class _FakeStdin:
            def isatty(self):
                return True

        try:
            sys.stdin = _FakeStdin()
            # Force platform.system() to a non-Windows value
            platform.system = lambda: "Linux"
            # Monkeypatch pexpect.spawn
            pexpect.spawn = fake_spawn

            rc, out = run_cmd("echo 'ignored by fake'", verbose=True, cwd=None)

            # Verify we got the fake child's exit status and combined output
            self.assertEqual(rc, 0)
            self.assertIn("mocked-pexpect-output", out)
            self.assertIn("second-line", out)
        finally:
            # Restore originals
            sys.stdin = old_stdin
            platform.system = old_platform_system
            if old_pexpect_spawn is None:
                # remove attribute if it didn't exist before
                try:
                    delattr(pexpect, "spawn")
                except Exception:
                    # fallback: set to None
                    pexpect.spawn = None
            else:
                pexpect.spawn = old_pexpect_spawn
