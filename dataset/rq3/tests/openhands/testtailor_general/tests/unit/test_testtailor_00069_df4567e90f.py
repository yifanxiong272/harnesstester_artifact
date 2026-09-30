import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.utils.runtime_build')
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
        """When the provided base_image already includes the runtime repo we
        should hit the branch that logs "already a valid runtime image" and
        simply return the repo and tag (adding :latest when missing).
        """
        # Ensure we use the same runtime repo as the code under test
        runtime_repo = get_runtime_image_repo()

        with patch.object(logger, "debug") as mock_debug:
            # Case 1: repo without explicit tag -> should append :latest
            base_image_no_tag = f"{runtime_repo}"
            repo, tag = get_runtime_image_repo_and_tag(base_image_no_tag)
            self.assertEqual(repo, runtime_repo)
            self.assertEqual(tag, "latest")

            # Case 2: repo with explicit tag -> should return that tag
            base_image_with_tag = f"{runtime_repo}:custom-tag"
            repo2, tag2 = get_runtime_image_repo_and_tag(base_image_with_tag)
            self.assertEqual(repo2, runtime_repo)
            self.assertEqual(tag2, "custom-tag")

            # Ensure logger.debug was called for both invocations with the expected message
            expected_msg_no_tag = (
                f"The provided image [{base_image_no_tag}] is already a valid runtime image.\n"
                f"Will try to reuse it as is."
            )
            expected_msg_with_tag = (
                f"The provided image [{base_image_with_tag}] is already a valid runtime image.\n"
                f"Will try to reuse it as is."
            )

            # Two calls expected (one per invocation)
            self.assertEqual(mock_debug.call_count, 2)
            called_msgs = [args[0] for args, _ in mock_debug.call_args_list]
            self.assertIn(expected_msg_no_tag, called_msgs)
            self.assertIn(expected_msg_with_tag, called_msgs)
