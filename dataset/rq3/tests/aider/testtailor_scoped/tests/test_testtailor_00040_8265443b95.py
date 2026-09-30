import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.base_coder')
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
        """Ensure that passing edit_format='code' triggers the branch that normalizes it and
        still selects a coder whose class.edit_format matches the resolved value (None)."""
        created = {}

        class DummyCoder:
            # This coder advertises an edit_format of None so it should be selected
            edit_format = None

            def __init__(self, main_model, io, **kwargs):
                # record that we were instantiated and with which args
                created["main_model"] = main_model
                created["io"] = io
                created["kwargs"] = kwargs

        # Patch the coders registry to only include our DummyCoder
        with patch("aider.coders.__all__", [DummyCoder]):
            main_model = MagicMock()
            # Make the main model report edit_format == None so that
            # create(..., edit_format='code') -> edit_format becomes None and matches DummyCoder
            main_model.edit_format = None

            io = MagicMock()

            # Call the classmethod under test
            res = Coder.create(main_model=main_model, edit_format="code", io=io)

            # The returned object should be an instance of our DummyCoder
            self.assertIsInstance(res, DummyCoder)

            # And the constructor should have received the main_model and io we passed
            self.assertIs(created.get("main_model"), main_model)
            self.assertIs(created.get("io"), io)
