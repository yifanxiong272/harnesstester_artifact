import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.agents')
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
        """Ensure a warning is emitted when put_demos_in_history is True and demonstration_template is set."""
        # Create a lightweight handler that captures formatted log messages in a list
        class ListHandler(logging.Handler):
            def __init__(self):
                super().__init__(level=logging.WARNING)
                self.records = []

            def emit(self, record):
                try:
                    msg = self.format(record)
                except Exception:
                    msg = record.getMessage()
                self.records.append(msg)

        logger = logging.getLogger("swea-config")
        # Save and remove existing handlers to make behavior deterministic, then add our handler
        old_handlers = list(logger.handlers)
        for h in old_handlers:
            logger.removeHandler(h)

        handler = ListHandler()
        # Use a simple formatter to keep message text readable
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)

        try:
            # Instantiate TemplateConfig to trigger the model_validator 'warnings' after-validator
            cfg = TemplateConfig(put_demos_in_history=True, demonstration_template="demo")
            # Check that our handler captured the expected warning
            all_logged = "\n".join(handler.records)
            self.assertIn(
                "demonstration_template is ignored when put_demos_in_history is True",
                all_logged,
            )
            # sanity check the object was created
            self.assertIsInstance(cfg, TemplateConfig)
        finally:
            # restore original handlers to avoid side effects on other tests
            logger.removeHandler(handler)
            for h in old_handlers:
                logger.addHandler(h)
