import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.args_formatter')
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
        heading = "MyHeading"

        # capture what is passed to the base HelpFormatter.start_section
        saved = argparse.HelpFormatter.start_section
        captured = {}

        def fake_start_section(self, h):
            captured['heading'] = h
            return saved(self, h)

        argparse.HelpFormatter.start_section = fake_start_section
        try:
            fmt = DotEnvFormatter("prog")
            fmt.start_section(heading)
        finally:
            argparse.HelpFormatter.start_section = saved

        expected = "\n\n" + "#" * (len(heading) + 3) + f"\n# {heading}"
        self.assertEqual(captured.get('heading'), expected)
