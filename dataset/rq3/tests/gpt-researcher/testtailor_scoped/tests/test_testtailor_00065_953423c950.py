import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.deep_research')
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
        """Ensure parse_search_queries_response uses parsed dict keys:
        - prefers 'queries' when present
        - falls back to 'searchQueries'
        - falls back to 'items'
        and trims whitespace and respects num_queries.
        """
        # 'queries' key (should be preferred)
        response_queries = '{"queries":[{"query":" q1 ","researchGoal":" g1 "},{"query":"q2","researchGoal":"g2"}]}'
        result_queries = parse_search_queries_response(response_queries, num_queries=3)
        self.assertEqual(
            result_queries,
            [{"query": "q1", "researchGoal": "g1"}, {"query": "q2", "researchGoal": "g2"}],
        )

        # missing 'queries', use 'searchQueries' and respect num_queries limit
        response_search_queries = '{"searchQueries":[{"query":"qA","researchGoal":"gA"},{"query":"qB","researchGoal":"gB"}]}'
        result_search_queries = parse_search_queries_response(response_search_queries, num_queries=1)
        self.assertEqual(result_search_queries, [{"query": "qA", "researchGoal": "gA"}])

        # missing both, use 'items'
        response_items = '{"items":[{"query":"x","researchGoal":"y"}]}'
        result_items = parse_search_queries_response(response_items, num_queries=5)
        self.assertEqual(result_items, [{"query": "x", "researchGoal": "y"}])
