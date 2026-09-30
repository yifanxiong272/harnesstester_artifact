import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.utils')
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
        """Trigger the UnicodeEncodeError path in stream_output and verify logger.error is used with replacements"""
        # prepare inputs: websocket None so (not websocket or output_log) is True and type != 'images'
        output = "hello 😁"  # contains an emoji not representable in cp1252
        content = {"foo": "bar"}

        # Construct a UnicodeEncodeError with a str object (second arg must be str)
        unicode_exc = UnicodeEncodeError("cp1252", output, 6, 7, "reason")

        # Patch logger.info to raise the UnicodeEncodeError and capture logger.error calls
        with unittest.mock.patch.object(logger, "info", side_effect=unicode_exc):
            with unittest.mock.patch.object(logger, "error") as mock_error:
                # get asyncio without a top-level import
                loop = __import__("asyncio").get_event_loop()
                loop.run_until_complete(
                    stream_output("text", content, output, websocket=None, output_log=True)
                )

                # expected: characters not encodable in cp1252 are replaced
                expected = output.encode("cp1252", errors="replace").decode("cp1252")
                mock_error.assert_called_once_with(expected)
