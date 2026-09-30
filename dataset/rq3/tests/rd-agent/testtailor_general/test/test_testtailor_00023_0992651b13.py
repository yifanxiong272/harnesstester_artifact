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
        """Test generate_RAG_content takes the vector RAG path and uses topk_k=1 when mini_case is True."""
        # create a fake vector_base with a searchable method
        class FakeVectorBase:
            def __init__(self):
                self.called = False
                self.last_args = None

            def search_experience(self, target, hypothesis_and_feedback, topk_k=1):
                self.called = True
                self.last_args = (target, hypothesis_and_feedback, topk_k)

                class Doc:
                    def __init__(self, content):
                        self.content = content

                # return a list of docs and a dummy second value
                return [Doc("content_a"), Doc("content_b")], None

        # minimal scenario stub satisfying conditions
        class ScenStub:
            def __init__(self):
                self.if_using_vector_rag = True
                self.mini_case = True
                self.vector_base = FakeVectorBase()

        scen = ScenStub()
        # trace is not used in the vector_rag branch, so a simple object is fine
        trace = object()

        result = generate_RAG_content(scen, trace, hypothesis_and_feedback="feedback text", target="target_text")

        # The function should join document contents with newline
        self.assertEqual(result, "content_a\ncontent_b")
        # verify the vector search was invoked with topk_k=1 and correct args
        self.assertTrue(scen.vector_base.called)
        self.assertEqual(scen.vector_base.last_args, ("target_text", "feedback text", 1))
