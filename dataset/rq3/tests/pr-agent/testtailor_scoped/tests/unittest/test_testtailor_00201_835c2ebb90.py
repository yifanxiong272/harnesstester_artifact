import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.token_handler')
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
        # Ensure we can trigger the "content too large" branch without allocating huge strings
        original_size = TokenHandler.CLAUDE_MAX_CONTENT_SIZE
        TokenHandler.CLAUDE_MAX_CONTENT_SIZE = 10  # make threshold tiny for test

        # Install a fake anthropic module so import anthropic and anthropic.Anthropic(...) succeed
        import sys, types
        fake_module = types.ModuleType("anthropic")

        class FakeAnthropicClient:
            def __init__(self, api_key=None):
                # messages attribute present but won't be called in this test path
                self.messages = types.SimpleNamespace(
                    count_tokens=lambda *a, **k: types.SimpleNamespace(input_tokens=42)
                )

        fake_module.Anthropic = FakeAnthropicClient
        sys.modules['anthropic'] = fake_module

        # Ensure the model key used exists in MAX_TOKENS
        from pr_agent.algo import MAX_TOKENS
        model_key = next(iter(MAX_TOKENS.keys()))
        get_settings(use_context=False).config.model = model_key

        # Capture if a warning is emitted on the global logger
        logger = get_logger()
        orig_warning = logger.warning
        warning_called = {'count': 0, 'msg': None}

        def fake_warning(msg):
            warning_called['count'] += 1
            warning_called['msg'] = msg

        logger.warning = fake_warning

        try:
            th = TokenHandler(system="sys", user="usr")
            # Create patch longer than the tiny CLAUDE_MAX_CONTENT_SIZE to trigger the branch
            patch = "x" * 20  # > 10 bytes
            result = th._calc_claude_tokens(patch)

            # Should return the max_tokens value for the configured model
            expected = MAX_TOKENS[model_key]
            self.assertEqual(result, expected)

            # And the warning should have been called once
            self.assertEqual(warning_called['count'], 1)
            self.assertIn("Content too large for Anthropic token counting API", warning_called['msg'])
        finally:
            # restore mutated globals / modules
            TokenHandler.CLAUDE_MAX_CONTENT_SIZE = original_size
            logger.warning = orig_warning
            if 'anthropic' in sys.modules:
                del sys.modules['anthropic']
