import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.extraction.schema_utils')
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
		"""Nested object schema with no properties should resolve to plain dict type."""
		schema = {
			'type': 'object',
			'properties': {
				# Nested object with no 'properties' key → should resolve to dict
				'metadata': {'type': 'object'},
			},
			'required': ['metadata'],
		}
		Model = schema_dict_to_pydantic_model(schema)
		# Should accept a plain dict for the metadata field
		instance = Model(metadata={'foo': 'bar'})
		self.assertEqual(instance.metadata, {'foo': 'bar'})
