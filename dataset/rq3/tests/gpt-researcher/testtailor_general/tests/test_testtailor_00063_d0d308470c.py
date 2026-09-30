import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.logging_config')
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
        """Test that setup_research_logging configures the 'research' logger and returns JSONResearchHandler."""
        # Run the function under test
        log_path, json_path, research_logger, json_handler = setup_research_logging()

        # Basic return value shape checks
        self.assertIsInstance(log_path, str)
        self.assertIsInstance(json_path, str)
        self.assertTrue(log_path.endswith(".log"))
        self.assertTrue(json_path.endswith(".json"))

        # logs directory should exist
        self.assertTrue(os.path.isdir("logs"))

        # Logger checks
        self.assertEqual(research_logger.name, "research")
        self.assertFalse(research_logger.propagate)

        # Ensure a FileHandler is attached and it writes to the expected file (match by basename or absolute path)
        has_file_handler = False
        for h in research_logger.handlers:
            base = getattr(h, "baseFilename", None)
            if base is not None:
                try:
                    if os.path.abspath(base) == os.path.abspath(log_path) or os.path.basename(base) == os.path.basename(log_path):
                        has_file_handler = True
                        break
                except Exception:
                    if os.path.basename(base) == os.path.basename(log_path):
                        has_file_handler = True
                        break
        self.assertTrue(has_file_handler, "Expected a FileHandler writing to the returned log path")

        # Write a log entry to ensure the file is created and written to
        try:
            research_logger.info("test log entry for unit test")
        except Exception as e:
            self.fail(f"Logging an entry raised an exception: {e}")

        # Now the log file should exist
        self.assertTrue(os.path.exists(log_path), "Expected the log file to be created after logging")

        # Ensure formatters were applied (check formatter format string on handlers)
        expected_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        has_expected_formatter = any(
            getattr(h, "formatter", None) is not None and getattr(h.formatter, "_fmt", None) == expected_fmt
            for h in research_logger.handlers
        )
        self.assertTrue(has_expected_formatter, "Expected handlers to use the configured formatter")

        # JSON handler checks: allow json_handler.json_file to be a Path or str
        self.assertIsInstance(json_handler, JSONResearchHandler)
        self.assertEqual(str(json_handler.json_file), json_path)

        # Cleanup: remove handlers and close file handles, remove created files/dir
        for h in list(research_logger.handlers):
            try:
                research_logger.removeHandler(h)
            except Exception:
                pass
            try:
                h.close()
            except Exception:
                pass

        # Remove created log file if exists
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
        except Exception:
            pass

        # Remove created json file if exists
        try:
            if os.path.exists(json_path):
                os.remove(json_path)
        except Exception:
            pass

        # Remove logs directory if empty
        try:
            if os.path.isdir("logs") and not os.listdir("logs"):
                os.rmdir("logs")
        except Exception:
            pass
