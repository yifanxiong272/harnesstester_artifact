import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.bitbucket_data_center.service.features')
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
        """Ensure get_repository_details_from_repo_name is awaited and content is returned."""
        ai = __import__('asyncio')

        class MyClient(BitbucketDCFeaturesMixin):
            def __init__(self):
                self._called = False

            async def get_repository_details_from_repo_name(self, repository):
                # mark that this method was called and return object with main_branch
                self._called = True

                class RepoDetails:
                    main_branch = "main"

                return RepoDetails()

            def _extract_owner_and_repo(self, repository):
                return ("PROJ", "repo")

            def _repo_api_base(self, owner, repo):
                return "http://base"

            async def _make_request(self, file_url, params=None):
                # return a response shaped like Bitbucket DC browse with lines
                return ({"lines": [{"text": "line1"}, {"text": "line2"}]}, None)

            def _parse_microagent_content(self, content, file_path):
                # return a simple object matching MicroagentContentResponse interface
                class Resp:
                    def __init__(self, content, path):
                        self.content = content
                        self.path = path
                        self.triggers = []
                        self.git_provider = None

                return Resp(content, file_path)

        client = MyClient()
        loop = ai.new_event_loop()
        try:
            ai.set_event_loop(loop)
            result = loop.run_until_complete(
                client.get_microagent_content("PROJ/repo", "path/to/file.md")
            )
        finally:
            loop.close()
            ai.set_event_loop(None)

        self.assertTrue(client._called, "Repository details method was not called")
        self.assertEqual(result.content, "line1\nline2")
        self.assertEqual(result.path, "path/to/file.md")
        self.assertEqual(result.triggers, [])
