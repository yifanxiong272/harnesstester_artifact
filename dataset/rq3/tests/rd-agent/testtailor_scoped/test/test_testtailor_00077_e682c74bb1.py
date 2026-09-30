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
        """Verify KGKnowledgeDocument initializes and stores all provided metadata fields."""
        # Create an instance with all fields set
        doc = KGKnowledgeDocument(
            content="sample content",
            label="test-label",
            embedding=[0.1, 0.2, 0.3],
            identity="identity-123",
            competition_name="Titanic Challenge",
            task_category="classification",
            field="feature-engineering",
            ranking=5,
            score=0.987,
            entities=[{"name": "Passenger", "type": "entity"}],
            relations=[{"from": "Passenger", "to": "Survived", "type": "related_to"}],
        )

        # Assert base fields set by super().__init__
        self.assertEqual(doc.content, "sample content")
        self.assertEqual(doc.label, "test-label")
        # Assert competition-specific metadata assigned correctly
        self.assertEqual(doc.competition_name, "Titanic Challenge")
        self.assertEqual(doc.task_category, "classification")
        self.assertEqual(doc.field, "feature-engineering")
        self.assertEqual(doc.ranking, 5)
        self.assertAlmostEqual(doc.score, 0.987)
        self.assertEqual(doc.entities, [{"name": "Passenger", "type": "entity"}])
        self.assertEqual(
            doc.relations, [{"from": "Passenger", "to": "Survived", "type": "related_to"}]
        )
