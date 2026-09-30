import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.utils.github')
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
        """When ref is None, _get_commit should return the first item from api.repos.list_commits."""
        commits = [{"sha": "abc123", "message": "first commit"}]

        class FakeRepos:
            def __init__(self):
                self.called = {}

            def list_commits(self, owner, repo):
                # record that this method was used with expected params
                self.called["owner"] = owner
                self.called["repo"] = repo
                return commits

            def get_commit(self, owner, repo, ref):
                raise AssertionError("get_commit should not be called when ref is None")

        fake_repos = FakeRepos()
        api = type("FakeApi", (), {"repos": fake_repos})()

        result = _get_commit(api, "owner1", "repo1", None)

        # should return the exact first commit object from the list
        self.assertIs(result, commits[0])
        # verify list_commits was called with the expected owner and repo
        self.assertEqual(fake_repos.called["owner"], "owner1")
        self.assertEqual(fake_repos.called["repo"], "repo1")
