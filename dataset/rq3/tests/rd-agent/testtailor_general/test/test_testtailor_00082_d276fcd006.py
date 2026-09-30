import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.kaggle.loop')
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
        """Ensure that when competition is provided, the setting is assigned and download_data is called,
        and the KaggleRDLoop is constructed and run with the provided step_n."""
        # import the module under test using built-in __import__ to avoid needing importlib
        module = __import__("rdagent.app.kaggle.loop", fromlist=["*"])

        # Patch download_data and KaggleRDLoop on the module to avoid heavy side effects
        with unittest.mock.patch.object(module, "download_data") as mock_download, unittest.mock.patch.object(
            module, "KaggleRDLoop"
        ) as mock_kaggle_loop_cls:
            # Prepare a mocked loop instance with a run method
            mock_loop_instance = mock_kaggle_loop_cls.return_value
            mock_loop_instance.run = unittest.mock.MagicMock()

            # Keep a reference to the settings object passed into main
            settings_obj = module.KAGGLE_IMPLEMENT_SETTING

            # Call main with a competition name and a step_n
            module.main(path=None, step_n=3, competition="some_competition")

            # Assertions: download_data should be called with competition and settings
            mock_download.assert_called_once_with(competition="some_competition", settings=settings_obj)

            # KaggleRDLoop should be instantiated with the settings object and run called with step_n
            mock_kaggle_loop_cls.assert_called_once_with(settings_obj)
            mock_loop_instance.run.assert_called_once_with(step_n=3)
