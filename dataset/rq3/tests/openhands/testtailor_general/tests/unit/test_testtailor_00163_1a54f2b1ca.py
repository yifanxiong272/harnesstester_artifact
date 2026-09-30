import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.sandbox.preset_sandbox_spec_service')
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
        """Ensure pagination starts at index 0 when page_id is None."""
        svc = PresetSandboxSpecService(
            specs=[
                SandboxSpecInfo(id='spec1', command=['/bin/sh']),
                SandboxSpecInfo(id='spec2', command=['/bin/bash']),
            ]
        )

        async_mod = __import__('asyncio')
        loop = async_mod.new_event_loop()
        try:
            async_mod.set_event_loop(loop)
            page = loop.run_until_complete(svc.search_sandbox_specs(page_id=None, limit=1))
        finally:
            loop.close()
            async_mod.set_event_loop(None)

        # start_idx should be 0, so the first item is returned and next_page_id set to '1'
        self.assertEqual(len(page.items), 1)
        self.assertEqual(page.items[0].id, 'spec1')
        self.assertEqual(page.next_page_id, '1')
