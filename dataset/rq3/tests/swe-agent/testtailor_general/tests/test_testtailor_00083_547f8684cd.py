import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.problem_statement')
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
    def test_case_01(self):
        """Ensure problem_statement_from_simplified_input returns a FileProblemStatement
        when type is 'text_file' and that the file contents and id are set correctly.
        """
        # create a temporary file using a runtime import to avoid missing-import errors
        tempfile = __import__("tempfile")
        content = "sample problem statement for testing\nline2"
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            tmp.write(content.encode())
            tmp.flush()
            tmp.close()

            ps = problem_statement_from_simplified_input(input=tmp.name, type="text_file")

            # returned object should be a FileProblemStatement and point to the same path
            self.assertIsInstance(ps, FileProblemStatement)
            self.assertEqual(ps.path, Path(tmp.name))

            # get_problem_statement should read the file contents
            self.assertEqual(ps.get_problem_statement(), content)

            # id should be set to the first 6 chars of the sha256 of the file contents
            expected_id = hashlib.sha256(content.encode()).hexdigest()[:6]
            self.assertEqual(ps.id, expected_id)
        finally:
            os.remove(tmp.name)
