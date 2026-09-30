import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.knowledge_management.vector_base')
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
        # Instantiate with explicit values and None for entities/relations to hit the "or []" branches
        doc = KGKnowledgeDocument(
            content="sample content",
            label="post-1",
            competition_name="MyCompetition",
            task_category="classification",
            field="modeling",
            ranking=5,
            score=0.873,
            entities=None,
            relations=None,
        )

        # Check that superclass initialization and assignments happened
        self.assertEqual(doc.content, "sample content")
        self.assertEqual(doc.label, "post-1")

        # Check KG-specific fields set correctly
        self.assertEqual(doc.competition_name, "MyCompetition")
        self.assertEqual(doc.task_category, "classification")
        self.assertEqual(doc.field, "modeling")
        self.assertEqual(doc.ranking, 5)
        self.assertAlmostEqual(doc.score, 0.873)

        # entities and relations should default to empty lists when passed None
        self.assertIsInstance(doc.entities, list)
        self.assertEqual(doc.entities, [])
        self.assertIsInstance(doc.relations, list)
        self.assertEqual(doc.relations, [])

        # Now instantiate with provided entities/relations to ensure they are preserved
        ents = [{"type": "feature", "name": "f1"}, {"type": "metric", "name": "m1"}]
        rels = [("f1", "related_to", "m1")]
        doc2 = KGKnowledgeDocument(
            content="other",
            competition_name="OtherComp",
            task_category="regression",
            entities=ents,
            relations=rels,
        )

        self.assertEqual(doc2.entities, ents)
        self.assertEqual(doc2.relations, rels)
