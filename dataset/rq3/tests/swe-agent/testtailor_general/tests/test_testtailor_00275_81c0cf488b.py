import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.tools')
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
        """Ensure _get_state raises ValueError when state.json contains non-dict JSON."""
        # Minimal config object expected by ToolHandler
        class DummyConfig:
            def model_copy(self, deep=True):
                return self

        cfg = DummyConfig()
        cfg.env_variables = {}
        cfg.registry_variables = {}
        cfg.bundles = []
        cfg.commands = []
        cfg.install_timeout = 1
        cfg.state_commands = []  # no commands to run before reading state
        cfg.multi_line_command_endings = []
        cfg.submit_command = "__submit__"
        cfg.submit_command_end_name = "__end__"

        class DummyFilter:
            pass

        filt = DummyFilter()
        filt.blocklist = []
        filt.blocklist_standalone = []
        filt.block_unless_regex = {}
        cfg.filter = filt

        cfg.parse_function = lambda output, commands: ("", "")

        # Instantiate handler
        handler = ToolHandler(cfg)

        # Env stub that returns a JSON array (not a dict) for /root/state.json
        class DummyEnv:
            def read_file(self, path, encoding=None, errors=None):
                return json.dumps([1, 2, 3])

            def communicate(self, *args, **kwargs):
                return ""

        env = DummyEnv()

        with self.assertRaises(ValueError) as cm:
            handler.get_state(env)

        msg = str(cm.exception)
        self.assertIn("State commands must return a dictionary. Got", msg)
        self.assertIn("[1, 2, 3]", msg)
