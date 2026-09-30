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
        """Preselector.choose should call model.query and interpret the returned message to indices."""
        # Prepare a minimal config-like object
        class C:
            pass

        config = C()
        config.system_template = "SYSTEM_PROMPT"
        # instance_template must use jinja2-style variables
        config.instance_template = "problem: {{problem_statement}}; subs: {{submissions}}"
        config.submission_template = "{{submission}}"
        config.max_len_submission = 100
        config.model = "dummy"

        # Dummy model that returns a message containing indices on the last line
        class DummyModel:
            def __init__(self, message):
                self._message = message

            def query(self, messages):
                # emulate the real model response structure
                return {"message": self._message}

        # Minimal logger stub
        logger = C()
        logger.debug = lambda *a, **k: None
        logger.warning = lambda *a, **k: None
        logger.error = lambda *a, **k: None

        # Fake submission object compatible with format_submission / to_format_dict usage
        class FakeSubmission:
            def __init__(self, submission_text):
                self.info = {"submission": submission_text}

            def to_format_dict(self, *, suffix=""):
                return {"submission": self.info["submission"]}

        # Create a Preselector instance without running its __init__
        pre = object.__new__(Preselector)
        pre.config = config
        pre.logger = logger
        # Message where the last line contains indices "0 1"
        msg_text = "Some reasoning\nIndices: 0 1"
        pre.model = DummyModel(msg_text)

        # Call choose with two fake submissions
        problem_stmt = "Solve X"
        subs = [FakeSubmission("code1"), FakeSubmission("code2")]

        output = pre.choose(problem_stmt, subs)

        # Assertions: interpret should parse [0,1], response should match, and messages should be built
        self.assertEqual(output.chosen_idx, [0, 1])
        self.assertEqual(output.response, msg_text)
        # messages should be a list with system and user entries
        self.assertIsInstance(output.messages, list)
        self.assertEqual(output.messages[0]["role"], "system")
        self.assertEqual(output.messages[0]["content"], config.system_template)
        self.assertEqual(output.messages[1]["role"], "user")
        # The user content should include the problem statement and the rendered submissions
        self.assertIn(problem_stmt, output.messages[1]["content"])
        self.assertIn("code1", output.messages[1]["content"])
        self.assertIn("code2", output.messages[1]["content"])
