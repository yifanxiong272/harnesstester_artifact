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
        """Ensure convert_env_value is invoked when an env var overrides config value."""
        import os
        from gpt_researcher.config import Config, BaseConfig

        # Preserve originals to restore after test
        orig_annotations = BaseConfig.__annotations__.copy() if hasattr(BaseConfig, "__annotations__") else {}
        test_key = "TEST_KEY"
        try:
            # Ensure BaseConfig has an annotation for the test key (bool in this case)
            BaseConfig.__annotations__[test_key] = bool

            # Prepare instance without running __init__ to avoid side-effects
            cfg = object.__new__(Config)

            # Stub out parse_retrievers to avoid importing retriever utilities or validation
            cfg.parse_retrievers = lambda x: ["tavily"]

            # Set environment variable so env_value is not None and should be converted to bool True
            os.environ[test_key] = "true"

            # Call the targeted method with a config that provides a different default (False)
            cfg._set_attributes({test_key: False})

            # The attribute should be set on the instance in lowercase and reflect converted env value
            self.assertTrue(hasattr(cfg, test_key.lower()))
            self.assertIs(cfg.test_key, True)
        finally:
            # Cleanup: restore annotations and environment
            BaseConfig.__annotations__.clear()
            BaseConfig.__annotations__.update(orig_annotations)
            if test_key in os.environ:
                del os.environ[test_key]
