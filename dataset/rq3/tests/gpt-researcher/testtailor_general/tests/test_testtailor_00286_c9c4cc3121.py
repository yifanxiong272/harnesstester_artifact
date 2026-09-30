import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.app')
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
        """Trigger the branch where the frontend directory does not exist and a warning is logged."""
        # import asyncio locally to avoid relying on file-level imports
        asyncio = __import__("asyncio")

        # Ensure os.path.exists returns False so the frontend branch is not taken
        with unittest.mock.patch("os.path.exists", return_value=False):
            with unittest.mock.patch.object(logger, "warning") as mock_warn:
                async def _run_lifespan():
                    # Use async context manager form to drive the async generator used by lifespan
                    async with lifespan(app):
                        # once inside, startup has completed (the yield point in the generator)
                        return

                # Run the async context which executes startup (and then shutdown on exit)
                asyncio.run(_run_lifespan())

                # Verify that a warning about missing frontend directory was logged
                self.assertTrue(mock_warn.called, "Expected logger.warning to be called")
                called_msg = mock_warn.call_args[0][0]
                self.assertIn("Frontend directory not found", called_msg)
