import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.daemon')
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
        """Invoke main() with a fake Daemon and ensure it constructs the Daemon
        with the parsed args and exits with code 0 (os._exit is mocked)."""
        created = []

        class DummyDaemon:
            def __init__(self, *args, **kwargs):
                # capture whatever was passed to the constructor for assertions
                self._ctor_args = args
                self._ctor_kwargs = kwargs
                created.append(self)
                # Prevent main() finally block from attempting to write failed state
                self._is_shutting_down = True

            async def run(self):
                # Simulate a quick successful run
                return None

            def _write_state(self, phase: str) -> None:
                # Should not be called because _is_shutting_down is True
                raise AssertionError("_write_state should not be called in this test")

        # Prepare argv to exercise all parser options
        test_argv = [
            "prog",
            "--session", "mysession",
            "--headed",
            "--profile", "myprofile",
            "--cdp-url", "ws://127.0.0.1:9222",
            "--use-cloud",
            "--cloud-profile-id", "cloud123",
            "--cloud-proxy-country", "US",
            "--cloud-timeout", "7",
        ]

        def fake_exit(code: int):
            # Replace os._exit to raise SystemExit so the test can catch it
            raise SystemExit(code)

        with unittest.mock.patch("sys.argv", test_argv):
            with unittest.mock.patch("browser_use.skill_cli.daemon.Daemon", new=DummyDaemon):
                with unittest.mock.patch("os._exit", new=fake_exit):
                    # Import and call main while patches are active
                    from browser_use.skill_cli import daemon as daemon_mod

                    with self.assertRaises(SystemExit) as cm:
                        daemon_mod.main()

                    # os._exit should have been called with exit_code 0
                    self.assertEqual(cm.exception.code, 0)

        # Verify a DummyDaemon instance was created and received the expected kwargs
        self.assertTrue(created, "Daemon was not instantiated")
        inst = created[0]
        # Check some of the constructor keyword args match parsed CLI values
        self.assertEqual(inst._ctor_kwargs.get("session"), "mysession")
        self.assertTrue(inst._ctor_kwargs.get("headed"))
        self.assertEqual(inst._ctor_kwargs.get("profile"), "myprofile")
        self.assertEqual(inst._ctor_kwargs.get("cdp_url"), "ws://127.0.0.1:9222")
        self.assertTrue(inst._ctor_kwargs.get("use_cloud"))
        self.assertEqual(inst._ctor_kwargs.get("cloud_profile_id"), "cloud123")
        self.assertEqual(inst._ctor_kwargs.get("cloud_proxy_country_code"), "US")
        self.assertEqual(inst._ctor_kwargs.get("cloud_timeout"), 7)
