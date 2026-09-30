import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.markdown_processing')
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
        """Ensure headers are extracted and nested according to their levels."""
        markdown_text = "# Title\n\n## Subtitle\n\n### Subsubtitle\n\n# New Title"
        result = extract_headers(markdown_text)
        expected = [
            {
                "level": 1,
                "text": "Title",
                "children": [
                    {
                        "level": 2,
                        "text": "Subtitle",
                        "children": [
                            {"level": 3, "text": "Subsubtitle"}
                        ],
                    }
                ],
            },
            {"level": 1, "text": "New Title"},
        ]
        self.assertEqual(result, expected)
