import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.app_conversation.sql_app_conversation_info_service')
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
        """Ensure search_app_conversation_info orders by last_updated_at when sort_order is UPDATED_AT."""
        async def runner():
            # Create a minimal query-like object that records order_by calls
            class DummyQuery:
                def __init__(self):
                    self.order_by_arg = None
                    self.offset_n = None
                    self.limit_n = None

                def where(self, *args, **kwargs):
                    # Accept any where condition and return self for chaining
                    return self

                def order_by(self, arg):
                    self.order_by_arg = arg
                    return self

                def offset(self, n):
                    self.offset_n = n
                    return self

                def limit(self, n):
                    self.limit_n = n
                    return self

            query_mock = DummyQuery()

            # Minimal result object with scalars().all() returning empty list
            class _Scalars:
                def all(self):
                    return []

            class ResultMock:
                def scalars(self):
                    return _Scalars()

            async def secure_select():
                return query_mock

            class DummyDB:
                async def execute(self, query):
                    return ResultMock()

            # Instantiate service without calling its __init__ (to avoid required params)
            service = object.__new__(SQLAppConversationInfoService)
            # Patch required attributes/methods
            service._secure_select = secure_select
            service.db_session = DummyDB()

            # Call the async method under test with sort_order UPDATED_AT
            await service.search_app_conversation_info(sort_order=AppConversationSortOrder.UPDATED_AT)

            # Assert that order_by was called with last_updated_at column
            self.assertIs(
                query_mock.order_by_arg,
                StoredConversationMetadata.last_updated_at,
                "Expected ordering by StoredConversationMetadata.last_updated_at when sort_order is UPDATED_AT",
            )

        __import__('asyncio').run(runner())
