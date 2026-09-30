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
        """Ensure a SimpleBatchInstance with a github repo_name yields a GithubRepoConfig."""
        sb = SimpleBatchInstance(
            image_name="my-image:tag",
            problem_statement="solve this problem",
            instance_id="iid123",
            repo_name="https://github.com/example/repo",
            base_commit="abc123",
        )
        deployment = DockerDeploymentConfig(image="python:3.11")
        full = sb.to_full_batch_instance(deployment)

        # Repo should be recognized as a GitHub repo
        self.assertIsInstance(full.env.repo, GithubRepoConfig)
        self.assertEqual(full.env.repo.github_url, sb.repo_name)
        self.assertEqual(full.env.repo.base_commit, sb.base_commit)

        # Deployment should have image overridden by the SimpleBatchInstance image_name
        self.assertIsInstance(full.env.deployment, DockerDeploymentConfig)
        self.assertEqual(full.env.deployment.image, sb.image_name)

        # Problem statement propagated correctly
        self.assertIsInstance(full.problem_statement, TextProblemStatement)
        self.assertEqual(full.problem_statement.id, sb.instance_id)
        self.assertEqual(full.problem_statement.text, sb.problem_statement)
