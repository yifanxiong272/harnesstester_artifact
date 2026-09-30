import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.batch_instances')
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
        """to_full_batch_instance should raise if a LocalDeploymentConfig is given together with an image_name."""
        sbi = SimpleBatchInstance(image_name="some-image:latest", problem_statement="do something", instance_id="inst1")
        deployment = LocalDeploymentConfig()
        with self.assertRaises(ValueError) as cm:
            sbi.to_full_batch_instance(deployment)
        self.assertEqual(str(cm.exception), "Local deployment does not support image_name")
