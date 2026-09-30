import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.github_polling')
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
        """Test that async_handle_request constructs a PRAgent, calls its handle_request
        and that the notify lambda triggers git_provider.add_eyes_reaction with the comment id.
        """
        # Prepare inputs
        pr_url = "https://example.com/pr/1"
        rest_of_comment = "please review"
        comment_id = 999

        # Dummy git provider to observe calls
        class DummyGitProvider:
            def __init__(self):
                self.calls = []

            def add_eyes_reaction(self, cid):
                self.calls.append(cid)

        git_provider = DummyGitProvider()

        # Fake PRAgent to replace the real one in the module that defines async_handle_request
        class DummyAgent:
            def __init__(self):
                pass

            async def handle_request(self, pr_url_arg, request_arg, notify=None):
                # verify arguments forwarded correctly
                assert pr_url_arg == pr_url
                assert request_arg == rest_of_comment
                # Simulate notifying behavior
                if notify:
                    notify()
                return True

        # Patch the PRAgent symbol in the module where async_handle_request is defined
        module_name = async_handle_request.__module__
        module = __import__(module_name, fromlist=["*"])
        original_pra = getattr(module, "PRAgent", None)
        setattr(module, "PRAgent", DummyAgent)
        try:
            loop = asyncio.new_event_loop()
            try:
                res = loop.run_until_complete(
                    async_handle_request(pr_url, rest_of_comment, comment_id, git_provider)
                )
            finally:
                loop.close()
        finally:
            # restore original
            if original_pra is None:
                try:
                    delattr(module, "PRAgent")
                except Exception:
                    # if deletion fails, ignore to avoid masking test result
                    pass
            else:
                setattr(module, "PRAgent", original_pra)

        # Assertions: handle_request returned True and notify called git provider correctly
        self.assertTrue(res)
        self.assertEqual(git_provider.calls, [comment_id])
