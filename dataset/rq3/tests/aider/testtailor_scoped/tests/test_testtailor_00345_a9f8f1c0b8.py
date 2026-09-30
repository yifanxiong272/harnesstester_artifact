import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.gui')
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
        """Ensure gui_main calls streamlit.set_page_config and constructs the GUI."""
        import importlib
        import types
        from unittest import mock

        # Try a few likely module names until we find the module under test
        candidates = [
            "gui",
            "aider.gui",
            "aider.gui_main",
            "aider.web_ui",
            "main",
            "app",
        ]
        module = None
        for name in candidates:
            try:
                module = importlib.import_module(name)
                # prefer modules that expose gui_main
                if hasattr(module, "gui_main"):
                    break
            except Exception:
                module = None
        if module is None or not hasattr(module, "gui_main"):
            self.skipTest("Could not locate module with gui_main to test")

        # Prepare fake urls and fake streamlit (st) with a MagicMock for set_page_config
        fake_urls = types.SimpleNamespace(favicon="fav.ico", website="https://example.com")
        fake_st = types.SimpleNamespace(set_page_config=mock.MagicMock())

        # Replace module attributes so gui_main uses our fakes
        setattr(module, "urls", fake_urls)
        setattr(module, "st", fake_st)

        # Replace GUI with a dummy to avoid executing heavy UI logic on construction
        class DummyGUI:
            instantiated = False

            def __init__(self, *args, **kwargs):
                DummyGUI.instantiated = True

        setattr(module, "GUI", DummyGUI)

        # Call the function under test
        module.gui_main()

        # Assertions: set_page_config was called with expected high-level args
        fake_st.set_page_config.assert_called_once()
        call_args, call_kwargs = fake_st.set_page_config.call_args
        # Check key expected keyword args
        self.assertEqual(call_kwargs.get("layout"), "wide")
        self.assertEqual(call_kwargs.get("page_title"), "Aider")
        self.assertEqual(call_kwargs.get("page_icon"), fake_urls.favicon)
        self.assertIn("menu_items", call_kwargs)
        menu_items = call_kwargs["menu_items"]
        self.assertEqual(menu_items.get("Get Help"), fake_urls.website)
        # GUI should have been instantiated
        self.assertTrue(DummyGUI.instantiated)
