import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.plugins.jupyter.__init__')
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
        """Ensure LocalRuntime branch sets code_repo_path and launches jupyter via bash."""
        # Arrange: set LocalRuntime and OPENHANDS_REPO_PATH
        os.environ['LOCAL_RUNTIME_MODE'] = '1'
        code_repo_path = '/tmp/fake_repo_for_test'
        os.environ['OPENHANDS_REPO_PATH'] = code_repo_path

        # Prepare a fake subprocess returned by asyncio.create_subprocess_shell
        async def fake_create_subprocess_shell(cmd, stderr, stdout):
            # Confirm the command contains the cd to the repo (sanity check inside fake)
            assert f'cd {code_repo_path}\n' in cmd

            class FakeStdout:
                def __init__(self):
                    self._yielded = False

                async def readline(self):
                    # First call returns a line containing 'at' to trigger the startup break
                    if not self._yielded:
                        self._yielded = True
                        return b'Serving at http://0.0.0.0:12345\n'
                    await asyncio.sleep(0)
                    return b''

            class FakeProcess:
                def __init__(self):
                    self.stdout = FakeStdout()

            return FakeProcess()

        # Patch asyncio.create_subprocess_shell and JupyterPlugin.run (so we don't actually run kernels)
        with unittest.mock.patch.object(sys, 'platform', 'linux'):
            with unittest.mock.patch('asyncio.create_subprocess_shell', new=unittest.mock.AsyncMock(side_effect=fake_create_subprocess_shell)) as mock_create:
                # make run return a simple object with content attribute
                async def fake_run(self, action):
                    class DummyObs:
                        def __init__(self, content):
                            self.content = content

                    return DummyObs('/usr/bin/python\n')

                with unittest.mock.patch.object(JupyterPlugin, 'run', new=fake_run):
                    # Act: initialize plugin
                    plugin = JupyterPlugin()
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(plugin.initialize(username='anyuser'))

                    # Assert: create_subprocess_shell was invoked and plugin populated correctly
                    mock_create.assert_called()
                    self.assertTrue(hasattr(plugin, 'kernel_gateway_port'))
                    self.assertIsInstance(plugin.kernel_gateway_port, int)
                    self.assertEqual(plugin.python_interpreter_path, '/usr/bin/python')
