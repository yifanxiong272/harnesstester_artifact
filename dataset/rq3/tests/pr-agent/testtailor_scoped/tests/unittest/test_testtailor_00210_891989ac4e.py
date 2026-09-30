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
        """complete the test case here"""
        # Prepare a dummy settings object to be returned by get_settings()
        class DummySettings:
            def __init__(self):
                self.store = {
                    "gitlab.commands": ["auto_review --fast", "answer --extra=1"]
                }
                # config must be an object with attributes; set disable_auto_feedback False by default
                from types import SimpleNamespace
                self.config = SimpleNamespace(disable_auto_feedback=False)

            def get(self, key, default=None):
                return self.store.get(key, default)

            def set(self, key, value, merge=True):
                # support setting config.is_auto_command
                if key.startswith("config."):
                    attr = key.split(".", 1)[1]
                    setattr(self.config, attr, value)
                else:
                    self.store[key] = value

            def unset(self, key):
                if key in self.store:
                    del self.store[key]

        dummy_settings = DummySettings()

        # Prepare a dummy agent that records calls to handle_request
        calls = []

        class DummyAgent:
            async def handle_request(self, pr_url, request, notify=None):
                calls.append((pr_url, request))
                return True

        agent = DummyAgent()

        # Minimal logger that supports contextualize as a context manager and common logging methods
        from contextlib import contextmanager

        class DummyLogger:
            def __init__(self):
                self.messages = []

            def info(self, *args, **kwargs):
                self.messages.append(("info", args))

            def error(self, *args, **kwargs):
                self.messages.append(("error", args))

            def warning(self, *args, **kwargs):
                self.messages.append(("warning", args))

            def exception(self, *args, **kwargs):
                self.messages.append(("exception", args))

            def debug(self, *args, **kwargs):
                self.messages.append(("debug", args))

            @contextmanager
            def contextualize(self, **kwargs):
                yield self

        logger = DummyLogger()

        # Patch the function globals to use our dummy implementations
        with patch.dict(_perform_commands_gitlab.__globals__, {
            "get_settings": lambda use_context=False: dummy_settings,
            "apply_repo_settings": lambda pr_url: None,
            "should_process_pr_logic": lambda data: True,
            "update_settings_from_args": lambda args: args,
            "get_logger": lambda *a, **k: logger
        }):
            # Call the async function
            import asyncio
            data = {"object_attributes": {"title": "test"}}
            asyncio.get_event_loop().run_until_complete(
                _perform_commands_gitlab("commands", agent, "http://example.com/pr/1", {"ctx": "x"}, data)
            )

        # Assertions: settings flag should be set and agent should have been called for each command
        self.assertTrue(getattr(dummy_settings.config, "is_auto_command", False))
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], "http://example.com/pr/1")
        # Ensure the commands were composed with command name preserved
        self.assertTrue(calls[0][1].startswith("auto_review"))
        self.assertTrue(calls[1][1].startswith("answer"))
