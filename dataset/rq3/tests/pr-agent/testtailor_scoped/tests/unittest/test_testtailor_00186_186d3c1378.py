import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_add_docs')
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
        """complete the test case here"""
        # create instance without running __init__
        pr = PRAddDocs.__new__(PRAddDocs)

        # prepare minimal async _prepare_prediction that does nothing (will be invoked via retry)
        async def fake_prepare(model):
            # no-op, leave prediction handling to _prepare_pr_code_docs stub
            return None

        pr._prepare_prediction = fake_prepare

        # stub _prepare_pr_code_docs to return a valid structure containing 'Code Documentation'
        def fake_prepare_pr_code_docs():
            return {
                'Code Documentation': [
                    {
                        'relevant file': 'test.py',
                        'relevant line': 1,
                        'documentation': 'Example doc',
                        'doc placement': 'after'
                    }
                ]
            }

        pr._prepare_pr_code_docs = fake_prepare_pr_code_docs

        # capture logs
        captured = []

        class LoggerStub:
            def info(self, msg):
                captured.append(msg)
            def error(self, msg):
                captured.append("ERROR: " + str(msg))
            def debug(self, msg):
                # ignore debug messages
                pass
            def warning(self, msg, artifact=None):
                # ignore warnings
                pass

        # patch the globals used by PRAddDocs.run to ensure predictable behavior
        run_globals = PRAddDocs.run.__globals__
        orig_retry = run_globals.get('retry_with_fallback_models')
        orig_get_logger = run_globals.get('get_logger')
        orig_get_settings = run_globals.get('get_settings')

        try:
            # ensure publish_output is False so no git operations occur by providing a get_settings stub
            class SettingsStub:
                class Config:
                    publish_output = False
                    verbosity_level = 0
                    temperature = 0.0
                config = Config()
                def set(self, *a, **k):
                    pass

            run_globals['retry_with_fallback_models'] = (lambda f, model_type=None: f("fake-model"))  # will call the bound method
            run_globals['get_logger'] = (lambda *a, **k: LoggerStub())
            run_globals['get_settings'] = (lambda use_context=False: SettingsStub())

            # run the async method
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # create a new loop if the default is running
                    new_loop = asyncio.new_event_loop()
                    try:
                        new_loop.run_until_complete(pr.run())
                    finally:
                        new_loop.close()
                else:
                    loop.run_until_complete(pr.run())
            except RuntimeError:
                # fallback if no running loop
                asyncio.run(pr.run())

            # assert that the target log message was emitted
            self.assertIn('Generating code Docs for PR...', captured)
        finally:
            # restore globals
            if orig_retry is not None:
                run_globals['retry_with_fallback_models'] = orig_retry
            else:
                run_globals.pop('retry_with_fallback_models', None)
            if orig_get_logger is not None:
                run_globals['get_logger'] = orig_get_logger
            else:
                run_globals.pop('get_logger', None)
            if orig_get_settings is not None:
                run_globals['get_settings'] = orig_get_settings
            else:
                run_globals.pop('get_settings', None)
