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
        """Verify to_full_batch_instance returns a BatchInstance for LocalDeploymentConfig when image_name is empty."""
        # Create a SimpleBatchInstance with an empty image_name so LocalDeploymentConfig path is taken
        sbi = SimpleBatchInstance(image_name="", problem_statement="solve this", instance_id="inst_local")
        # Create a local deployment config to trigger the LocalDeploymentConfig branch
        deployment = LocalDeploymentConfig()
        # Invoke the method under test
        batch = sbi.to_full_batch_instance(deployment)
        # Assertions
        self.assertIsInstance(batch, BatchInstance)
        self.assertIsInstance(batch.env, EnvironmentConfig)
        # Local deployment should not set a repo when repo_name is empty
        self.assertIsNone(batch.env.repo)
        # Deployment in returned env should be a LocalDeploymentConfig and should be a deep copy (different identity)
        self.assertIsInstance(batch.env.deployment, LocalDeploymentConfig)
        self.assertIsNot(batch.env.deployment, deployment)
        # Problem statement id should match the instance_id passed in
        self.assertEqual(batch.problem_statement.id, "inst_local")
