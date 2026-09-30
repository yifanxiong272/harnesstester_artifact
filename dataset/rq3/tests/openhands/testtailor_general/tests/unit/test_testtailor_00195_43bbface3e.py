import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.config.agent_config')
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
        """Verify resolved_system_prompt_filename returns the configured filename
        (i.e., hits the branch that returns self.system_prompt_filename).
        """
        # Case 1: plan mode disabled -> should return the default filename
        cfg = AgentConfig()
        cfg.enable_plan_mode = False
        self.assertEqual(cfg.resolved_system_prompt_filename, 'system_prompt.j2')

        # Case 2: plan mode enabled but a custom filename was provided -> should return the custom filename
        cfg_custom = AgentConfig()
        cfg_custom.enable_plan_mode = True
        cfg_custom.system_prompt_filename = 'custom_system_prompt.j2'
        self.assertEqual(cfg_custom.resolved_system_prompt_filename, 'custom_system_prompt.j2')
