import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.help')
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
        """Verify HelpMessage.get_general_commands_text returns the expected commands text."""
        expected = (
            "> - **/review**: Request a review of your Pull Request.   \n"
            "> - **/describe**: Update the PR title and description based on the contents of the PR.   \n"
            "> - **/improve [--extended]**: Suggest code improvements. Extended mode provides a higher quality feedback.   \n"
            "> - **/ask \\<QUESTION\\>**: Ask a question about the PR.   \n"
            "> - **/update_changelog**: Update the changelog based on the PR's contents.   \n"
            "> - **/help_docs \\<QUESTION\\>**: Given a path to documentation (either for this repository or for a given one), ask a question.   \n"
            "> - **/add_docs**: Generate docstring for new components introduced in the PR.   \n"
            "> - **/generate_labels**: Generate labels for the PR based on the PR's contents.   \n\n"
            ">See the [tools guide](https://pr-agent-docs.codium.ai/tools/) for more details.\n"
            ">To list the possible configuration parameters, add a **/config** comment.   \n"
        )

        result = HelpMessage.get_general_commands_text()
        self.assertIsInstance(result, str)
        self.assertEqual(expected, result)
