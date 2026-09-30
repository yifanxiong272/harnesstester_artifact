import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.arxiv.arxiv')
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
        """Verify ArxivSearch __init__ sets arxiv, validates sort and maps sort to SortCriterion."""
        import importlib
        import sys

        # Try common module names where ArxivSearch might be defined, then fall back to loaded modules
        candidates = [
            'gpt_researcher.arxiv_search',
            'gpt_researcher.retrievers.arxiv',
            'gpt_researcher.arxiv',
            'arxiv_search',
            'arxiv'
        ]

        ArxivSearch = None
        target_mod = None
        for name in candidates:
            try:
                mod = importlib.import_module(name)
            except Exception:
                continue
            if hasattr(mod, 'ArxivSearch'):
                ArxivSearch = getattr(mod, 'ArxivSearch')
                target_mod = mod
                break

        if ArxivSearch is None:
            # fallback: search already-loaded modules
            for mod in list(sys.modules.values()):
                try:
                    if hasattr(mod, 'ArxivSearch'):
                        ArxivSearch = getattr(mod, 'ArxivSearch')
                        target_mod = mod
                        break
                except Exception:
                    continue

        self.assertIsNotNone(ArxivSearch, "Could not find ArxivSearch class in expected modules")

        # Create a fake arxiv module object with SortCriterion enum-like attributes
        class _SortCriterion:
            Relevance = 'FAKE_RELEVANCE'
            SubmittedDate = 'FAKE_SUBMITTED'

        fake_arxiv = type('fake_arxiv_mod', (), {'SortCriterion': _SortCriterion})

        # Inject the fake arxiv into the module where ArxivSearch is defined so the __init__ will use it
        setattr(target_mod, 'arxiv', fake_arxiv)

        # Case 1: default sort (should map to Relevance)
        inst1 = ArxivSearch(query='test-query-default')
        self.assertEqual(inst1.query, 'test-query-default')
        # instance should have the injected arxiv reference
        self.assertIs(inst1.arxiv, fake_arxiv)
        self.assertEqual(inst1.sort, fake_arxiv.SortCriterion.Relevance)

        # Case 2: explicit SubmittedDate sort
        inst2 = ArxivSearch(query='test-query-submitted', sort='SubmittedDate')
        self.assertEqual(inst2.sort, fake_arxiv.SortCriterion.SubmittedDate)

        # Case 3: invalid sort value should raise AssertionError
        with self.assertRaises(AssertionError):
            ArxivSearch(query='bad', sort='NotAValidSort')
