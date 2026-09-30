import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.service')
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
        """Verify DomService __init__ correctly assigns provided and default attributes."""
        # Minimal fake BrowserSession with a logger attribute
        class FakeBrowserSession:
            def __init__(self, logger):
                self.logger = logger

        # Use a dedicated logger objects to distinguish between browser_session.logger and explicit logger
        bs_logger = logging.getLogger("browser_session_logger")
        explicit_logger = logging.getLogger("explicit_logger")

        # Instantiate a browser session with its logger
        fake_bs = FakeBrowserSession(bs_logger)

        # 1) Test defaults: no explicit logger passed, default params used
        ds_default = DomService(browser_session=fake_bs)
        # browser_session should be the same object
        self.assertIs(ds_default.browser_session, fake_bs)
        # logger should default to browser_session.logger
        self.assertIs(ds_default.logger, bs_logger)
        # Defaults for flags and numeric values
        self.assertFalse(ds_default.cross_origin_iframes)
        self.assertTrue(ds_default.paint_order_filtering)
        self.assertEqual(ds_default.max_iframes, 100)
        self.assertEqual(ds_default.max_iframe_depth, 5)
        self.assertEqual(ds_default.viewport_threshold, 1000)

        # 2) Test explicit parameters override defaults (including explicit logger)
        ds_explicit = DomService(
            browser_session=fake_bs,
            logger=explicit_logger,
            cross_origin_iframes=True,
            paint_order_filtering=False,
            max_iframes=5,
            max_iframe_depth=2,
            viewport_threshold=None,
        )
        # browser_session still should be same object
        self.assertIs(ds_explicit.browser_session, fake_bs)
        # logger should be the explicit one we passed
        self.assertIs(ds_explicit.logger, explicit_logger)
        # Check that flags/values reflect what we passed
        self.assertTrue(ds_explicit.cross_origin_iframes)
        self.assertFalse(ds_explicit.paint_order_filtering)
        self.assertEqual(ds_explicit.max_iframes, 5)
        self.assertEqual(ds_explicit.max_iframe_depth, 2)
        self.assertIsNone(ds_explicit.viewport_threshold)
