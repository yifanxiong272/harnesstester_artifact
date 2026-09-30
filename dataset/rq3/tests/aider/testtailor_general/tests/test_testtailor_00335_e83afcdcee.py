import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.context_coder')
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
        """Ensure reply_completed sets abs_fnames to a fresh set and calls add_rel_fname for mentions."""
        # create instance without running __init__
        inst = object.__new__(ContextCoder)

        # non-empty partial response content so early return isn't taken
        inst.partial_response_content = "I think we need to change file1.py"

        # current in-chat files differ from mentioned files to force the branch
        inst.get_inchat_relative_files = lambda: ["file2.py"]
        inst.get_file_mentions = lambda content, ignore_current=True: ["file1.py"]

        # ensure we don't hit the reflections limit
        inst.num_reflections = 0
        inst.max_reflections = 3

        # record calls to add_rel_fname
        calls = []
        def add_rel_fname(fname):
            calls.append(fname)
        inst.add_rel_fname = add_rel_fname

        # provide gpt_prompts with try_again attribute used by the method
        inst.gpt_prompts = type("G", (), {"try_again": "please try again"})()
        inst.reflected_message = None

        # pre-populate abs_fnames with a non-empty value to ensure assignment happens
        inst.abs_fnames = {"should_be_cleared"}

        # Call method under test
        result = ContextCoder.reply_completed(inst)

        # Assertions: method returns True, abs_fnames is reset to a set, and add_rel_fname was called
        self.assertTrue(result)
        self.assertIsInstance(inst.abs_fnames, set)
        # abs_fnames should have been reset to an empty set by the assignment (loop then calls add_rel_fname)
        # since add_rel_fname does not modify abs_fnames in this test, it remains an empty set
        self.assertEqual(inst.abs_fnames, set())
        # add_rel_fname should have been called for the mentioned file
        self.assertEqual(calls, ["file1.py"])
