import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.integrations.forgejo.service.branches')
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
        # Create a dummy class that includes the mixin under test and implement required abstract methods
        class Dummy(ForgejoBranchesMixin):
            def _get_cursorrules_url(self, *args, **kwargs):
                return ""

            def _get_file_name_from_item(self, item):
                return ""

            def _get_file_path_from_item(self, item):
                return ""

            def _get_microagents_directory_params(self):
                return {}

            def _get_microagents_directory_url(self):
                return ""

            def _is_valid_microagent_file(self, item):
                return False

        instance = Dummy()

        # Create simple branch-like objects
        class DummyBranch:
            def __init__(self, name):
                self.name = name

        # Responses for two pages
        resp_page1 = type("Resp", (), {})()
        resp_page1.branches = [DummyBranch("main"), DummyBranch("dev")]
        resp_page1.has_next_page = True

        resp_page2 = type("Resp", (), {})()
        resp_page2.branches = [DummyBranch("feature")]
        resp_page2.has_next_page = False

        # Track calls to verify paging parameters
        called = {"pages": [], "per_pages": []}

        # Create an awaitable that returns immediately without using asyncio
        class Immediate:
            def __init__(self, value):
                self.value = value

            def __await__(self):
                if False:
                    yield None
                return self.value
                yield None

        def fake_get_paginated_branches(repository, page=1, per_page=30):
            called["pages"].append(page)
            called["per_pages"].append(per_page)
            if page == 1:
                return Immediate(resp_page1)
            return Immediate(resp_page2)

        # Patch the instance method with our stub (not async, but awaitable)
        instance.get_paginated_branches = fake_get_paginated_branches

        # Run the async get_branches coroutine without importing asyncio by driving its __await__ generator
        coro = instance.get_branches("owner/repo")
        gen = coro.__await__()
        try:
            next(gen)
        except StopIteration as e:
            result = e.value
        else:
            # If it yielded unexpectedly, exhaust to completion
            try:
                while True:
                    next(gen)
            except StopIteration as e:
                result = e.value

        # Assert we collected all branches across pages and in correct order
        self.assertEqual(len(result), 3)
        self.assertEqual([b.name for b in result], ["main", "dev", "feature"])

        # Assert paging behavior: started at page 1, then page 2, and used per_page=100
        self.assertEqual(called["pages"], [1, 2])
        self.assertTrue(all(p == 100 for p in called["per_pages"]))
