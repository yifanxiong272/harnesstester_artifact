import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.reviewer')
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
        """Test that build_messages renders instance and submission templates and returns proper roles."""
        # Prepare a minimal config with Jinja templates
        config = type("C", (), {})()
        config.instance_template = (
            "Problem: {{ problem_statement }}\n"
            "Submissions:\n"
            "{% for s in submissions %}- {{ s }}\n{% endfor %}"
        )
        config.submission_template = "Submission: {{ submission }}"
        config.system_template = "You are a system."
        config.max_len_submission = 100
        config.model = "dummy-model"

        # Dummy logger that captures debug messages
        class DummyLogger:
            def __init__(self):
                self.last_debug = None
            def debug(self, msg):
                self.last_debug = msg
            def warning(self, *args, **kwargs):
                pass
            def error(self, *args, **kwargs):
                pass

        # Create a fake submission object compatible with format_submission
        class DummySubmission:
            def __init__(self, submission_text):
                self.info = {"submission": submission_text}
                # to_format_dict should return keys referenced by submission_template
                self._fmt = {"submission": submission_text}
            def to_format_dict(self, *args, **kwargs):
                return self._fmt

        # Create Preselector instance without running __init__
        pre = Preselector.__new__(Preselector)
        pre.config = config
        pre.logger = DummyLogger()

        # Two submissions
        s1 = DummySubmission("print(1)")
        s2 = DummySubmission("print(2)")

        problem_statement = "Add two numbers."

        messages = pre.build_messages(problem_statement, [s1, s2])

        # Assertions on structure
        self.assertIsInstance(messages, list)
        self.assertEqual(len(messages), 2)

        # System message should be exactly the system_template
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], config.system_template)

        # User message should contain rendered problem statement and both rendered submissions
        self.assertEqual(messages[1]["role"], "user")
        user_content = messages[1]["content"]
        self.assertIn(problem_statement, user_content)
        self.assertIn("Submission: print(1)", user_content)
        self.assertIn("Submission: print(2)", user_content)

        # Logger should have captured the debug message containing the same user content
        self.assertEqual(pre.logger.last_debug, f"MODEL INPUT (user)\n{user_content}")
