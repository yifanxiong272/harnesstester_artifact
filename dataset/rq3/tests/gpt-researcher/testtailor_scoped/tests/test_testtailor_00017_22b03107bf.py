import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.config.config')
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
        """Ensure that when REPORT_SOURCE != 'web', _set_doc_path is called and doc_path is set."""
        # Use a deterministic path inside the current working directory to avoid needing tempfile import
        tmpdir = os.path.join(os.getcwd(), "tmp_test_doc_path_for_config")
        # Ensure the directory does not exist before the test
        if os.path.isdir(tmpdir):
            try:
                os.rmdir(tmpdir)
            except OSError:
                # If it's not empty or cannot be removed, choose a different name to avoid conflicts
                tmpdir = os.path.join(os.getcwd(), "tmp_test_doc_path_for_config_2")
                if os.path.isdir(tmpdir):
                    try:
                        os.rmdir(tmpdir)
                    except OSError:
                        pass

        fake_config = {"REPORT_SOURCE": "filesystem", "DOC_PATH": tmpdir}

        # Patch out other initialization steps to isolate _set_doc_path behavior
        with patch.object(Config, "load_config", return_value=fake_config), \
             patch.object(Config, "_set_attributes", return_value=None), \
             patch.object(Config, "_set_embedding_attributes", return_value=None), \
             patch.object(Config, "_set_llm_attributes", return_value=None), \
             patch.object(Config, "_handle_deprecated_attributes", return_value=None):
            try:
                cfg = Config(config_path="unused")

                # _set_doc_path should set doc_path to the value from the config
                self.assertTrue(hasattr(cfg, "doc_path"))
                self.assertEqual(cfg.doc_path, tmpdir)

                # The directory should exist (validate_doc_path uses os.makedirs)
                self.assertTrue(os.path.isdir(cfg.doc_path))
            finally:
                # Cleanup created directory if it exists
                if os.path.isdir(tmpdir):
                    try:
                        os.rmdir(tmpdir)
                    except OSError:
                        # If removal fails, ignore to avoid failing the test cleanup
                        pass
