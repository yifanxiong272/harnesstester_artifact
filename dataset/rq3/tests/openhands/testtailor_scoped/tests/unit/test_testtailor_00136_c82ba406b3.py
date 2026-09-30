import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.llm.llm_registry')
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
        """Ensure that providing agent_cls causes the registry to use it when resolving LLM config."""
        # Prepare a config
        config = OpenHandsConfig()
        called = {}

        # Patch OpenHandsConfig.get_llm_config_from_agent at the class level to avoid Pydantic attribute errors
        original_get_llm_config_from_agent = OpenHandsConfig.get_llm_config_from_agent

        def fake_get_llm_config_from_agent(self, name):
            # record the name that was requested
            called['name'] = name
            # return a minimal LLMConfig instance
            return LLMConfig()

        OpenHandsConfig.get_llm_config_from_agent = fake_get_llm_config_from_agent

        # Patch LLMRegistry.get_llm temporarily to avoid constructing a real LLM
        original_get_llm = LLMRegistry.get_llm

        def fake_get_llm(self, service_id, config=None):
            # Return a lightweight dummy object that resembles the LLM interface used by the registry
            class DummyLLM:
                def __init__(self, service_id, config):
                    self.service_id = service_id
                    self.config = config

            # emulate storing in registry as _create_new_llm would do
            dummy = DummyLLM(service_id, config)
            self.service_to_llm[service_id] = dummy
            return dummy

        LLMRegistry.get_llm = fake_get_llm

        try:
            registry = LLMRegistry(config=config, agent_cls='custom_agent_name')
            # Verify that the agent_cls value was passed into get_llm_config_from_agent
            self.assertIn('name', called)
            self.assertEqual(called['name'], 'custom_agent_name')

            # The registry still uses service_id 'agent' for the active LLM as per implementation
            self.assertEqual(registry.active_agent_llm.service_id, 'agent')
            # And the config returned should be an LLMConfig instance
            self.assertIsInstance(registry.active_agent_llm.config, LLMConfig)
        finally:
            # Restore original methods to avoid side effects on other tests
            OpenHandsConfig.get_llm_config_from_agent = original_get_llm_config_from_agent
            LLMRegistry.get_llm = original_get_llm
