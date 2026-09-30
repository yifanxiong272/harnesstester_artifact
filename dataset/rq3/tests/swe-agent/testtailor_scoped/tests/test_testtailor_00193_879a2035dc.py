import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.reviewer')
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
        """format_submission should return 'Solution invalid.' when submission is missing."""
        # Bypass __init__ to avoid model creation side-effects
        preselector = Preselector.__new__(Preselector)
        # minimal config with max_len_submission > 0 and a template
        cfg = type("C", (), {})()
        cfg.max_len_submission = 10
        cfg.submission_template = "{{submission}}"
        preselector.config = cfg

        # Dummy submission object: info has no 'submission' key so get(...) returns None
        class DummySubmission:
            def __init__(self):
                self.info = {}
            def to_format_dict(self, *args, **kwargs):
                return {}

        submission = DummySubmission()
        result = preselector.format_submission("some problem", submission)
        self.assertEqual(result, "Solution invalid.")
