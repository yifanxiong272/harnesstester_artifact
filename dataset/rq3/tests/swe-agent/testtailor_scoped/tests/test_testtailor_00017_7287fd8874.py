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
        """Ensure to_format_dict uses a deepcopy of info and adds missing submission."""
        # Create instance using pydantic's construct to avoid validation/attr setup issues
        rs = ReviewSubmission.construct(info={"id": "123", "meta": {"attempts": 2}}, trajectory=None, model_stats=None)

        # Precondition: original info does not contain 'submission'
        self.assertNotIn("submission", rs.info)

        out = rs.to_format_dict(suffix="_suf")

        # Expect string fields and nested dict fields to be flattened with suffix,
        # and missing 'submission' to be added as empty string in the output
        expected = {"id_suf": "123", "meta_attempts_suf": 2, "submission_suf": ""}
        self.assertEqual(out, expected)

        # The original info object should remain unchanged (deepcopy used)
        self.assertNotIn("submission", rs.info)
