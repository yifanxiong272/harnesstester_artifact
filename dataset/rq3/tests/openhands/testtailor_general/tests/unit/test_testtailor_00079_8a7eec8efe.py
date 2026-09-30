import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.utils.sql_utils')
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
        """Ensure JsonTypeDecorator delegates to the TypeAdapter's dump_python and validate_python."""
        # Replace the TypeAdapter used by create_json_type_decorator with a fake one
        orig_type_adapter = create_json_type_decorator.__globals__.get('TypeAdapter', None)

        class FakeTypeAdapter:
            _last_instance = None

            def __init__(self, obj_type):
                # record instance for later inspection
                FakeTypeAdapter._last_instance = self
                self.obj_type = obj_type
                self.last_dump_args = None
                self.last_validate_args = None

            def dump_python(self, value, mode=None, context=None):
                # record arguments and return a sentinel
                self.last_dump_args = (value, mode, context)
                return {'dumped': True, 'value': value, 'mode': mode, 'context': context}

            def validate_python(self, value):
                # record argument and return a sentinel
                self.last_validate_args = (value,)
                return f'validated:{value}'

        try:
            # Patch the global TypeAdapter name used by the function
            create_json_type_decorator.__globals__['TypeAdapter'] = FakeTypeAdapter

            # Create the JSON type decorator class for a sample type (dict)
            JsonTDClass = create_json_type_decorator(dict)
            # Instantiate the decorator (SQLAlchemy would normally do this)
            decorator_instance = JsonTDClass()

            # Call process_bind_param and verify it used our fake adapter
            input_bind = {'a': 1}
            bind_result = decorator_instance.process_bind_param(input_bind, dialect=None)
            self.assertEqual(
                bind_result,
                {
                    'dumped': True,
                    'value': input_bind,
                    'mode': 'json',
                    'context': {'expose_secrets': True},
                },
            )

            # Inspect the fake adapter instance to ensure it received the expected args
            adapter_instance = FakeTypeAdapter._last_instance
            self.assertIsNotNone(adapter_instance, "TypeAdapter instance was not created")
            self.assertEqual(adapter_instance.last_dump_args[0], input_bind)
            self.assertEqual(adapter_instance.last_dump_args[1], 'json')
            self.assertEqual(adapter_instance.last_dump_args[2], {'expose_secrets': True})

            # Call process_result_param and verify it used validate_python
            input_result = {'b': 2}
            result = decorator_instance.process_result_param(input_result, dialect=None)
            self.assertEqual(result, f'validated:{input_result}')
            self.assertEqual(adapter_instance.last_validate_args, (input_result,))
        finally:
            # Restore original TypeAdapter if it existed
            if orig_type_adapter is None:
                create_json_type_decorator.__globals__.pop('TypeAdapter', None)
            else:
                create_json_type_decorator.__globals__['TypeAdapter'] = orig_type_adapter
