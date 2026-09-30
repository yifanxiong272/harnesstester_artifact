import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run')
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
        """Ensure the 'run-api' command imports and calls sweagent.api.server.run_from_cli with remaining args."""
        server_name = "sweagent.api.server"
        api_name = "sweagent.api"
        pkg_name = "sweagent"

        # Save previous modules to restore later
        old_server = sys.modules.get(server_name)
        old_api = sys.modules.get(api_name)
        old_pkg = sys.modules.get(pkg_name)

        called = []

        # Create stub module objects using the same type as existing modules
        server_mod = type(sys)(server_name)
        def fake_run_from_cli(args):
            called.append(list(args))
        setattr(server_mod, "run_from_cli", fake_run_from_cli)

        api_mod = type(sys)(api_name)
        # optional: provide attribute pointing to submodule
        setattr(api_mod, "server", server_mod)

        pkg_mod = type(sys)(pkg_name)
        setattr(pkg_mod, "api", api_mod)

        try:
            # Inject into sys.modules so the dynamic import inside main() resolves to our stubs
            sys.modules[pkg_name] = pkg_mod
            sys.modules[api_name] = api_mod
            sys.modules[server_name] = server_mod

            # Call the CLI main with the target command and some dummy remaining args
            cmd = ["run-api", "--bind", "127.0.0.1:1234", "--verbose"]
            main(cmd)

            # Verify our stub was called exactly once with the remaining args
            self.assertEqual(len(called), 1)
            self.assertEqual(called[0], ["--bind", "127.0.0.1:1234", "--verbose"])
        finally:
            # Restore previous sys.modules state
            if old_server is None:
                sys.modules.pop(server_name, None)
            else:
                sys.modules[server_name] = old_server

            if old_api is None:
                sys.modules.pop(api_name, None)
            else:
                sys.modules[api_name] = old_api

            if old_pkg is None:
                sys.modules.pop(pkg_name, None)
            else:
                sys.modules[pkg_name] = old_pkg
