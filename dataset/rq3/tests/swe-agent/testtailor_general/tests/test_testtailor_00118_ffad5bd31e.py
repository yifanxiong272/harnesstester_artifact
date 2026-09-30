import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.environment.repo')
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
        """repo_from_simplified_input returns a GithubRepoConfig when type=='github'."""
        url = "https://github.com/example-org/example-repo"
        base = "main"
        cfg = repo_from_simplified_input(input=url, base_commit=base, type="github")
        self.assertIsInstance(cfg, GithubRepoConfig)
        self.assertEqual(cfg.github_url, url)
        self.assertEqual(cfg.base_commit, base)
        self.assertEqual(cfg.type, "github")
