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
        """Ensure parse_search_queries_response selects from 'queries', then 'searchQueries', then 'items'."""
        # When only searchQueries is present, it's used and whitespace is stripped
        response_search = (
            '{"searchQueries": ['
            '{"query": " q1 ", "researchGoal": " g1 "},'
            '{"query": "q2", "researchGoal": "g2"}'
            ']}'
        )
        result_search = parse_search_queries_response(response_search, num_queries=10)
        self.assertEqual(
            result_search,
            [{"query": "q1", "researchGoal": "g1"}, {"query": "q2", "researchGoal": "g2"}],
        )

        # When only items is present, it's used
        response_items = '{"items": [{"query": "a", "researchGoal": "b"}]}'
        result_items = parse_search_queries_response(response_items, num_queries=1)
        self.assertEqual(result_items, [{"query": "a", "researchGoal": "b"}])

        # When both queries and searchQueries are present, 'queries' should take precedence
        response_both = (
            '{"queries":[{"query":"X","researchGoal":"GX"}],'
            '"searchQueries":[{"query":"Y","researchGoal":"GY"}]}'
        )
        result_both = parse_search_queries_response(response_both, num_queries=2)
        self.assertEqual(result_both, [{"query": "X", "researchGoal": "GX"}])
