import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.mcp.utils')
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
        """Test that convert_mcp_clients_to_tools captures exceptions, logs an error, records it, and returns an empty list."""
        # Import the utils module without adding an import statement at top
        utils = __import__("openhands.mcp.utils", fromlist=["*"])

        # Create a mock tool whose to_param raises an exception to trigger the except block
        mock_tool = unittest.mock.MagicMock()
        mock_tool.to_param.side_effect = Exception("conversion failure")

        # Create a mock client that contains the failing tool
        mock_client = unittest.mock.MagicMock()
        mock_client.tools = [mock_tool]

        # Replace the module's mcp_error_collector and logger.error with mocks to avoid side effects
        mock_collector = unittest.mock.MagicMock()
        mock_collector.add_error = unittest.mock.MagicMock()
        utils.mcp_error_collector = mock_collector
        utils.logger.error = unittest.mock.MagicMock()

        # Call the function under test
        result = utils.convert_mcp_clients_to_tools([mock_client])

        # The function should return an empty list on exception
        self.assertEqual(result, [])

        # Verify the error collector was called once with the expected keyword arguments
        expected_error_message = "Error in convert_mcp_clients_to_tools: conversion failure"
        mock_collector.add_error.assert_called_once_with(
            server_name="general",
            server_type="conversion",
            error_message=expected_error_message,
            exception_details="conversion failure",
        )
