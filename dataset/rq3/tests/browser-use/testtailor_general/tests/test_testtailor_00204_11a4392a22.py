import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.controller')
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
        """MCPToolWrapper __init__ raises ImportError when MCP SDK is not available"""
        import sys
        import importlib

        # Try to locate the module that defines MCPToolWrapper by scanning loaded modules first
        target_mod = None
        for m in list(sys.modules.values()):
            if not m:
                continue
            if hasattr(m, 'MCPToolWrapper'):
                target_mod = m
                break

        # If not already loaded, try a list of candidate module names
        if target_mod is None:
            candidates = [
                'browser_use.tools.mcp',
                'browser_use.tools.mcp_tool_wrapper',
                'browser_use.tools.mcp_tool',
                'browser_use.tools.mcp_wrapper',
                'browser_use.tools.mcp_tools',
            ]
            for name in candidates:
                try:
                    mod = importlib.import_module(name)
                    if hasattr(mod, 'MCPToolWrapper'):
                        target_mod = mod
                        break
                except Exception:
                    continue

        if target_mod is None or not hasattr(target_mod, 'MCPToolWrapper'):
            self.skipTest('Could not locate module containing MCPToolWrapper')

        # Backup original flag (if present) and force MCP as unavailable
        original_flag = getattr(target_mod, 'MCP_AVAILABLE', True)
        try:
            setattr(target_mod, 'MCP_AVAILABLE', False)
            with self.assertRaises(ImportError) as cm:
                # registry can be any object since __init__ only assigns it
                target_mod.MCPToolWrapper(registry=object(), mcp_command='npx')
            self.assertIn('MCP SDK not installed', str(cm.exception))
        finally:
            # Restore original state
            try:
                setattr(target_mod, 'MCP_AVAILABLE', original_flag)
            except Exception:
                # If restoration fails for any reason, ignore to not mask test result
                pass
