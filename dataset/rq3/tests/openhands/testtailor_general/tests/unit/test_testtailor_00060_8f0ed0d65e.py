import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.plugins.jupyter.execute_server')
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
        """Ensure make_app constructs a JupyterKernel with env vars and initializes it, returning a Tornado app."""
        # Prepare environment
        old_port = os.environ.get('JUPYTER_GATEWAY_PORT')
        old_kid = os.environ.get('JUPYTER_GATEWAY_KERNEL_ID')
        os.environ['JUPYTER_GATEWAY_PORT'] = '9999'
        os.environ['JUPYTER_GATEWAY_KERNEL_ID'] = 'kid'

        # Replace the JupyterKernel symbol used by make_app with a test double stored in make_app's globals
        original_kernel_cls = make_app.__globals__.get('JupyterKernel')

        created = {}

        class DummyKernel:
            def __init__(self, url_suffix: str, convid: str, lang: str = 'python') -> None:
                # record construction args and instance
                created['url_suffix'] = url_suffix
                created['convid'] = convid
                created['lang'] = lang
                created['instance'] = self
                # make initialize an awaitable that does nothing
                self.initialize = unittest.mock.AsyncMock(return_value=None)

        try:
            make_app.__globals__['JupyterKernel'] = DummyKernel

            # Call the function under test
            app = make_app()

            # Assert that the kernel was constructed with values derived from the environment
            self.assertEqual(created.get('url_suffix'), 'localhost:9999')
            self.assertEqual(created.get('convid'), 'kid')
            self.assertEqual(created.get('lang'), 'python')

            # The initialize coroutine should have been awaited (run_until_complete)
            inst = created.get('instance')
            self.assertIsNotNone(inst, "Kernel instance was not created")
            # AsyncMock marks .called True when awaited
            self.assertTrue(getattr(inst.initialize, 'called', False), "initialize() was not awaited")

            # The function should return a Tornado Application instance
            self.assertIsInstance(app, tornado.web.Application)

        finally:
            # Restore environment and original class
            if original_kernel_cls is None:
                del make_app.__globals__['JupyterKernel']
            else:
                make_app.__globals__['JupyterKernel'] = original_kernel_cls

            # restore env variables
            if old_port is None:
                del os.environ['JUPYTER_GATEWAY_PORT']
            else:
                os.environ['JUPYTER_GATEWAY_PORT'] = old_port

            if old_kid is None:
                del os.environ['JUPYTER_GATEWAY_KERNEL_ID']
            else:
                os.environ['JUPYTER_GATEWAY_KERNEL_ID'] = old_kid
