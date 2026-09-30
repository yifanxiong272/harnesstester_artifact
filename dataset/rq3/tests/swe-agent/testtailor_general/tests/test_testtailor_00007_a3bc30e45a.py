import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.inspector.static')
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
        """Test that _load_file builds history HTML with proper role mapping, role classes, and escaping."""
        history = [
            {"role": "user", "content": "Hello <world>", "agent": "primary"},
            {"role": "assistant", "content": "Hi there", "agent": "secondary"},
            {"role": "unknown", "content": "<script>bad</script>"},
        ]
        fake_content = {"history": history}

        # Monkeypatch load_content in the _load_file global namespace
        orig = _load_file.__globals__.get("load_content", None)
        _load_file.__globals__["load_content"] = lambda file_name, gold_patches, test_patches: fake_content
        try:
            result = _load_file("dummy_name", None, None)
        finally:
            # Restore original
            if orig is None:
                del _load_file.__globals__["load_content"]
            else:
                _load_file.__globals__["load_content"] = orig

        # Check that each history item id appears
        self.assertIn('id="historyItem0"', result)
        self.assertIn('id="historyItem1"', result)
        self.assertIn('id="historyItem2"', result)

        # First item: role is 'user' -> role_class 'user' and role_name from role_map -> 'Computer'
        self.assertIn('class="history-item user"', result)
        self.assertIn('<span>Computer</span>', result)
        self.assertIn('<pre>Hello &lt;world&gt;</pre>', result)

        # Second item: agent != 'primary' -> subroutine role_class, role_name for assistant -> 'SWE-Agent'
        self.assertIn('class="history-item subroutine"', result)
        self.assertIn('<div class="role-bar subroutine"><strong><span>SWE-Agent</span></strong></div>', result)
        self.assertIn('<pre>Hi there</pre>', result)

        # Third item: unknown role (not in role_map) -> role_name falls back to the role string, and content is escaped
        self.assertIn('<span>unknown</span>', result)
        self.assertIn('<pre>&lt;script&gt;bad&lt;/script&gt;</pre>', result)
