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
        """Ensure get_default_config maps CONFIG.load_config and CONFIG keys correctly."""
        # Prepare fake config data returned by CONFIG.load_config()
        config_data = {
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
            'agent': {
                'name': 'agent1',
                'version': 'v1',
            },
        }

        # Save originals to restore after test
        orig_load = CONFIG.load_config
        orig_openai = getattr(CONFIG, 'OPENAI_API_KEY', None)
        orig_anthropic = getattr(CONFIG, 'ANTHROPIC_API_KEY', None)
        orig_google = getattr(CONFIG, 'GOOGLE_API_KEY', None)
        orig_deepseek = getattr(CONFIG, 'DEEPSEEK_API_KEY', None)
        orig_grok = getattr(CONFIG, 'GROK_API_KEY', None)

        try:
            # Patch CONFIG attributes
            CONFIG.load_config = lambda: config_data
            CONFIG.OPENAI_API_KEY = 'openai-global'
            CONFIG.ANTHROPIC_API_KEY = 'anthropic-global'
            CONFIG.GOOGLE_API_KEY = 'google-global'
            CONFIG.DEEPSEEK_API_KEY = 'deepseek-global'
            CONFIG.GROK_API_KEY = 'grok-global'

            result = get_default_config()

            expected = {
                'model': {
                    'name': 'gpt-4',
                    'temperature': 0.7,
                    'api_keys': {
                        # llm.api_key should override CONFIG.OPENAI_API_KEY
                        'OPENAI_API_KEY': 'llm-key',
                        'ANTHROPIC_API_KEY': 'anthropic-global',
                        'GOOGLE_API_KEY': 'google-global',
                        'DEEPSEEK_API_KEY': 'deepseek-global',
                        'GROK_API_KEY': 'grok-global',
                    },
                },
                'agent': {
                    'name': 'agent1',
                    'version': 'v1',
                },
                'browser': {
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
                'command_history': [],
            }

            self.assertEqual(result, expected)
        finally:
            # Restore originals
            CONFIG.load_config = orig_load
            if orig_openai is None:
                try:
                    delattr(CONFIG, 'OPENAI_API_KEY')
                except AttributeError:
                    pass
            else:
                CONFIG.OPENAI_API_KEY = orig_openai

            if orig_anthropic is None:
                try:
                    delattr(CONFIG, 'ANTHROPIC_API_KEY')
                except AttributeError:
                    pass
            else:
                CONFIG.ANTHROPIC_API_KEY = orig_anthropic

            if orig_google is None:
                try:
                    delattr(CONFIG, 'GOOGLE_API_KEY')
                except AttributeError:
                    pass
            else:
                CONFIG.GOOGLE_API_KEY = orig_google

            if orig_deepseek is None:
                try:
                    delattr(CONFIG, 'DEEPSEEK_API_KEY')
                except AttributeError:
                    pass
            else:
                CONFIG.DEEPSEEK_API_KEY = orig_deepseek

            if orig_grok is None:
                try:
                    delattr(CONFIG, 'GROK_API_KEY')
                except AttributeError:
                    pass
            else:
                CONFIG.GROK_API_KEY = orig_grok
