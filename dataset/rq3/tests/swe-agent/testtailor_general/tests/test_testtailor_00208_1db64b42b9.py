import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.merge_predictions')
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
        """Verify the CLI parser defines the expected arguments and types."""
        parser = get_cli_parser()
        # parser object created
        self.assertIsInstance(parser, argparse.ArgumentParser)

        # parse with multiple directories and an output
        args = parser.parse_args(["/tmp/one", "/tmp/two", "--output", "/tmp/out"])
        self.assertEqual(len(args.directories), 2)
        # directories should be pathlib.Path instances with expected values
        self.assertTrue(all(isinstance(p, Path) for p in args.directories))
        self.assertEqual([str(p) for p in args.directories], ["/tmp/one", "/tmp/two"])
        self.assertTrue(isinstance(args.output, Path))
        self.assertEqual(str(args.output), "/tmp/out")

        # parse with a single directory and no output -> output should be None
        args2 = parser.parse_args(["single_dir"])
        self.assertEqual(len(args2.directories), 1)
        self.assertEqual(str(args2.directories[0]), "single_dir")
        self.assertIsNone(args2.output)

        # missing required positional argument should cause SystemExit from argparse
        with self.assertRaises(SystemExit):
            parser.parse_args([])
