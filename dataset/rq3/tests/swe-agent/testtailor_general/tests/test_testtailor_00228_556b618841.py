import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.open_pr')
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
        """Ensure branch for a fork (forker != owner) triggers adding fork remote with token prefix."""
        # Import the module using built-in __import__ to avoid needing an import statement
        mod = __import__("sweagent.run.hooks.open_pr", fromlist=["*"])

        # Read the module source and replace the forker assignment so we can trigger the branch
        path = mod.__file__
        src = open(path, "r", encoding="utf-8").read()
        if "forker = owner" not in src:
            self.fail("Expected 'forker = owner' in source to replace it for the test")
        new_src = src.replace("forker = owner", "forker = 'different-owner'")

        # Execute the modified source in the module namespace to redefine open_pr in-place
        exec(compile(new_src, path, "exec"), mod.__dict__)

        # Provide fake implementations to avoid network/git calls
        class FakeIssue:
            number = 42
            title = "Example issue title"

        def fake_get_issue(issue_url, *, token=""):
            return FakeIssue()

        def fake_parse_issue_url(issue_url: str):
            # owner deliberately different from the hardcoded forker we injected ('different-owner')
            return ("orig-owner", "some-repo", "42")

        types = __import__("types")

        def fake_pulls_create(**kwargs):
            return types.SimpleNamespace(html_url="https://fake/pr/42")

        class FakeGhApi:
            def __init__(self, token=None):
                self.pulls = types.SimpleNamespace(create=fake_pulls_create)

        # Simple env that records communicate calls
        class DummyEnv:
            def __init__(self):
                self.calls = []

            def communicate(self, input: str, timeout: int = 25, **kwargs):
                # record the input exactly as passed
                self.calls.append(input.strip())
                return "ok-output"

        # Patch module-level names
        mod._get_gh_issue_data = fake_get_issue
        mod._parse_gh_issue_url = fake_parse_issue_url
        mod.GhApi = FakeGhApi

        env = DummyEnv()
        logging = __import__("logging")
        logger = logging.getLogger("test-open-pr")

        # Call the redefined open_pr with a token so token_prefix is used and _dry_run to avoid actual PR creation
        mod.open_pr(logger=logger, token="tok123", env=env, github_url="https://github.com/orig-owner/some-repo/issues/42", trajectory=[], _dry_run=True)

        # There should be a call that adds the fork remote with the token prefix and our injected forker
        expected_remote_cmd = "git remote add fork https://tok123@github.com/different-owner/some-repo.git"
        # Normalize recorded calls and assert presence
        self.assertTrue(any(expected_remote_cmd in call for call in env.calls), f"Expected remote add call not found in {env.calls}")
