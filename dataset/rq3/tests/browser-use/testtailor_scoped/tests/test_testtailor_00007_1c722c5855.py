import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.cli')
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
        """Verify get_default_config builds config from CONFIG.load_config and CONFIG defaults."""
        # Prepare a dummy CONFIG to inject into the function's globals
        class DummyConfig:
            OPENAI_API_KEY = 'global-openai'
            ANTHROPIC_API_KEY = 'global-anthropic'
            GOOGLE_API_KEY = 'global-google'
            DEEPSEEK_API_KEY = 'global-deepseek'
            GROK_API_KEY = 'global-grok'

            @staticmethod
            def load_config():
                return {
                    'browser_profile': {
                        'headless': False,
                        'keep_alive': False,
                        'ignore_https_errors': True,
                        'user_data_dir': '/tmp/user',
                        'allowed_domains': ['example.com'],
                        'wait_between_actions': 1.5,
                        'is_mobile': True,
                        'device_scale_factor': 2,
                        'disable_security': True,
                    },
                    'llm': {
                        'model': 'gpt-4',
                        'temperature': 0.7,
                        'api_key': 'llm-key',
                    },
                    'agent': {'name': 'agent-x', 'version': 1},
                }

        # Inject DummyConfig into the target function's global namespace
        fn_globals = get_default_config.__globals__
        original_config = fn_globals.get('CONFIG', None)
        fn_globals['CONFIG'] = DummyConfig

        try:
            cfg = get_default_config()

            # Validate top-level keys
            self.assertIn('model', cfg)
            self.assertIn('agent', cfg)
            self.assertIn('browser', cfg)
            self.assertIn('command_history', cfg)

            # Validate model block
            model = cfg['model']
            self.assertEqual(model['name'], 'gpt-4')
            self.assertEqual(model['temperature'], 0.7)
            api_keys = model['api_keys']
            # OPENAI_API_KEY should come from llm.api_key
            self.assertEqual(api_keys['OPENAI_API_KEY'], 'llm-key')
            # Other keys should come from DummyConfig attributes
            self.assertEqual(api_keys['ANTHROPIC_API_KEY'], 'global-anthropic')
            self.assertEqual(api_keys['GOOGLE_API_KEY'], 'global-google')
            self.assertEqual(api_keys['DEEPSEEK_API_KEY'], 'global-deepseek')
            self.assertEqual(api_keys['GROK_API_KEY'], 'global-grok')

            # Validate agent block passthrough
            self.assertEqual(cfg['agent'], {'name': 'agent-x', 'version': 1})

            # Validate browser block
            browser = cfg['browser']
            self.assertFalse(browser['headless'])
            self.assertFalse(browser['keep_alive'])
            self.assertTrue(browser['ignore_https_errors'])
            self.assertEqual(browser['user_data_dir'], '/tmp/user')
            self.assertEqual(browser['allowed_domains'], ['example.com'])
            self.assertEqual(browser['wait_between_actions'], 1.5)
            self.assertTrue(browser['is_mobile'])
            self.assertEqual(browser['device_scale_factor'], 2)
            self.assertTrue(browser['disable_security'])

            # Command history should be initialized empty
            self.assertEqual(cfg['command_history'], [])
        finally:
            # Restore original CONFIG to avoid side effects
            if original_config is None:
                fn_globals.pop('CONFIG', None)
            else:
                fn_globals['CONFIG'] = original_config
