import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.servers.gitlab_webhook')
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
        """Ensure apply_repo_settings is invoked at the start of _perform_commands_gitlab."""
        api_url = "http://gitlab.example.com/project/1"
        commands_conf = "any_commands"
        log_context = {"key": "value"}
        data = {}
        agent = object()

        module_prefix = _perform_commands_gitlab.__module__
        from unittest.mock import patch
        import asyncio

        with patch(f"{module_prefix}.apply_repo_settings") as mock_apply, \
             patch(f"{module_prefix}.should_process_pr_logic", return_value=False) as mock_should:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_perform_commands_gitlab(commands_conf, agent, api_url, log_context, data))

        mock_apply.assert_called_once_with(api_url)
        mock_should.assert_called_once_with(data)
