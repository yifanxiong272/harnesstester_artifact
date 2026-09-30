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
        """Test open_pr goes through git commands and uses expected branch naming when _dry_run=True."""
        # Dummy logger that records calls
        class DummyLogger:
            def __init__(self):
                self.infos = []
                self.debugs = []

            def info(self, *args, **kwargs):
                self.infos.append(args)

            def debug(self, *args, **kwargs):
                self.debugs.append(args)

        # Dummy environment that records commands passed to communicate
        class DummyEnv:
            def __init__(self):
                self.commands = []

            def communicate(self, input, timeout=None, *, check="ignore", error_msg=None):
                # Record the exact input string
                self.commands.append(input)
                # Return a predictable output
                return f"OK: {input}"

        logger = DummyLogger()
        env = DummyEnv()

        # Create a simple issue-like object
        issue_obj = type("Issue", (), {"number": "1", "title": "Test issue"})()

        # Patch the functions used inside open_pr in the module where open_pr is defined,
        # so we avoid network calls and control random.random
        with patch("sweagent.run.hooks.open_pr._get_gh_issue_data", return_value=issue_obj), patch(
            "sweagent.run.hooks.open_pr._parse_gh_issue_url", return_value=("owner", "repo", "1")
        ), patch("sweagent.run.hooks.open_pr.random.random", return_value=0.12345678):
            # Call open_pr with dry-run to avoid creating a real PR
            open_pr(
                logger=logger,
                token="",
                env=env,
                github_url="https://github.com/owner/repo/issues/1",
                trajectory=[{"response": "resp", "observation": "obs"}],
                _dry_run=True,
            )

        # Now assert that the expected git commands were invoked in order (presence checks)

        # 1. git config user
        assert any("git config user.email" in c and "git config user.name" in c for c in env.commands), env.commands

        # 2. remove model.patch
        assert any(c == "rm -f model.patch" for c in env.commands), env.commands

        # Expected deterministic branch given patched random.random()
        expected_branch = "swe-agent-fix-#1-12345678"

        # 3. checkout new branch with exact branch name
        assert any(c == f"git checkout -b {expected_branch}" for c in env.commands), env.commands

        # 4. git add .
        assert any(c == "git add ." for c in env.commands), env.commands

        # 5. git commit called with both message parts (braced placeholders should appear literally)
        assert any("git commit -m" in c and "Fix: {issue.title}" in c and "Closes #{issue.number}" in c for c in env.commands), env.commands

        # 6. push was invoked (dry-run uses echo prefix)
        assert any("git push origin" in c and expected_branch in c for c in env.commands), env.commands
