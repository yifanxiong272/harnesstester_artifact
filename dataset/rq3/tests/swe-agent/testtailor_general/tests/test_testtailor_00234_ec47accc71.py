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
        """Ensure repo_name containing a slash produces a LocalRepoConfig."""
        # Create a SimpleBatchInstance that should be interpreted as a local repo (contains '/')
        sb = SimpleBatchInstance(
            image_name="my-special-image:latest",
            problem_statement="Solve X",
            instance_id="inst-123",
            repo_name="some/local/repo",
            base_commit="deadbeef",
        )

        # Use a DockerDeploymentConfig so we go through the branch that sets deployment.image
        deployment = DockerDeploymentConfig(image="python:3.11")

        full = sb.to_full_batch_instance(deployment)

        # The repo should be a LocalRepoConfig because repo_name contains a slash
        self.assertIsInstance(full.env.repo, LocalRepoConfig)

        # Path should correspond to the provided repo_name
        self.assertEqual(str(full.env.repo.path), sb.repo_name)

        # Base commit should be propagated
        self.assertEqual(full.env.repo.base_commit, sb.base_commit)

        # Deployment image should be overridden with the SimpleBatchInstance.image_name
        self.assertIsInstance(full.env.deployment, DockerDeploymentConfig)
        self.assertEqual(full.env.deployment.image, sb.image_name)

        # Problem statement should be preserved
        self.assertIsInstance(full.problem_statement, TextProblemStatement)
        self.assertEqual(full.problem_statement.text, sb.problem_statement)
        self.assertEqual(full.problem_statement.id, sb.instance_id)
