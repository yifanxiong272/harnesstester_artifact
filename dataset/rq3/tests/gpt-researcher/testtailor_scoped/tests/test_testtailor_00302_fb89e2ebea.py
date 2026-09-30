import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.report_type.deep_research.example')
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
        """When no 'learnings' argument is provided, deep_research should initialize learnings to an empty list."""
        async def fake_generate_serp_queries(query, num_queries=3):
            # Return no queries so the code path initializes learnings and returns immediately
            return []

        dr = DeepResearch(query="test query", breadth=3, depth=1)
        # Replace the async generator with our stub
        dr.generate_serp_queries = fake_generate_serp_queries

        # Run the async deep_research and verify returned structure uses empty learnings
        result = asyncio.run(dr.deep_research(query="test query", breadth=3, depth=1))

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('learnings'), [])
        self.assertEqual(result.get('visited_urls'), [])
        self.assertEqual(result.get('citations'), {})
