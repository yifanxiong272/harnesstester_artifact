import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.chat.chat')
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
        """Verify _process_document uses RecursiveCharacterTextSplitter with expected parameters and returns split chunks"""
        # Prepare a sample report
        report = "This is a sample report. " * 10

        # Capture what the stub sees
        captured = {}

        # Create a stub class to replace RecursiveCharacterTextSplitter
        class StubSplitter:
            def __init__(self, *args, **kwargs):
                # record init kwargs for assertions
                captured['init_args'] = args
                captured['init_kwargs'] = kwargs

            def split_text(self, text):
                # record input text and return predictable chunks
                captured['split_text_arg'] = text
                return ["chunk-A", "chunk-B"]

        # Patch the name in the method's global namespace
        globals_dict = ChatAgentWithMemory._process_document.__globals__
        original = globals_dict.get('RecursiveCharacterTextSplitter', None)
        globals_dict['RecursiveCharacterTextSplitter'] = StubSplitter

        try:
            # Create an instance without running __init__ to avoid side effects
            dummy_self = ChatAgentWithMemory.__new__(ChatAgentWithMemory)

            # Call the method under test
            documents = ChatAgentWithMemory._process_document(dummy_self, report)

            # Assertions: returned documents come from our stub
            self.assertEqual(documents, ["chunk-A", "chunk-B"])

            # Assert the splitter was initialized with the expected kwargs
            self.assertIn('init_kwargs', captured)
            init_kwargs = captured['init_kwargs']
            self.assertEqual(init_kwargs.get('chunk_size'), 1024)
            self.assertEqual(init_kwargs.get('chunk_overlap'), 20)
            # length_function should be the builtin len
            self.assertIs(init_kwargs.get('length_function'), len)
            self.assertEqual(init_kwargs.get('is_separator_regex'), False)

            # Assert split_text was called with the original report
            self.assertEqual(captured.get('split_text_arg'), report)
        finally:
            # Restore original name to avoid side effects on other tests
            if original is None:
                globals_dict.pop('RecursiveCharacterTextSplitter', None)
            else:
                globals_dict['RecursiveCharacterTextSplitter'] = original
