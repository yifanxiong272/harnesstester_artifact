import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.proposal.proposal')
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
        """complete the test case here"""
        # Dummy document to mimic vector DB document with .content attribute
        class DummyDoc:
            def __init__(self, content):
                self.content = content

        # Dummy vector base to capture call and return predictable results
        class DummyVectorBase:
            def __init__(self):
                self.called_with = None

            def search_experience(self, target, hypothesis_and_feedback, topk_k=5):
                # record parameters for assertions
                self.called_with = {"target": target, "hypothesis_and_feedback": hypothesis_and_feedback, "topk_k": topk_k}
                # return a list of dummy docs and a placeholder metadata
                return [DummyDoc("doc_content_1")], None

        # Minimal fake scenario object to trigger the vector RAG branch
        class DummyScen:
            pass

        scen = DummyScen()
        scen.if_using_vector_rag = True
        scen.mini_case = True  # ensure topk_k=1 path
        scen.vector_base = DummyVectorBase()

        # trace is not used in this branch; pass None
        result = generate_RAG_content(scen, None, hypothesis_and_feedback="some feedback", target="my_target")

        # The returned content should be the joined contents of returned docs
        self.assertEqual(result, "doc_content_1")
        # Ensure the vector search was called with topk_k == 1 due to mini_case == True
        self.assertIsNotNone(scen.vector_base.called_with)
        self.assertEqual(scen.vector_base.called_with["topk_k"], 1)
        self.assertEqual(scen.vector_base.called_with["target"], "my_target")
        self.assertEqual(scen.vector_base.called_with["hypothesis_and_feedback"], "some feedback")
