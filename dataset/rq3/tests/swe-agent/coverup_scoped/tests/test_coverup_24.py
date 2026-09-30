# file: sweagent/agent/models.py:144-159
# asked: {"lines": [149, 152, 154, 155, 156, 157, 158], "branches": [[148, 149], [151, 152], [153, 154], [156, 157], [156, 159]]}
# gained: {"lines": [149, 152, 154, 155, 156, 157, 158], "branches": [[148, 149], [151, 152], [153, 154], [156, 157]]}

import os
import pytest
from pydantic import SecretStr

import sweagent.agent.models as models
from sweagent.agent.models import GenericAPIModelConfig


def test_get_api_keys_when_none_returns_empty():
    cfg = GenericAPIModelConfig(name="test-none")
    result = cfg.get_api_keys()
    assert result == []


def test_get_api_keys_when_empty_secret_returns_empty():
    cfg = GenericAPIModelConfig(name="test-empty", api_key=SecretStr(""))
    result = cfg.get_api_keys()
    assert result == []


def test_get_api_keys_env_var_not_set_logs_and_returns_empty(monkeypatch):
    env_name = "MISSING_ENV_FOR_TEST"
    # Ensure the environment variable is not set
    monkeypatch.delenv(env_name, raising=False)

    # Create a fake logger to capture the warning call
    class FakeLogger:
        def __init__(self):
            self.last_warning = None
            self.init_args = None
            self.init_kwargs = None

        def warning(self, msg):
            self.last_warning = msg

    def fake_get_logger(*args, **kwargs):
        logger = FakeLogger()
        logger.init_args = args
        logger.init_kwargs = kwargs
        # attach so we can inspect after call
        fake_get_logger.logger = logger
        return logger

    # Patch the get_logger used inside the module
    monkeypatch.setattr(models, "get_logger", fake_get_logger)

    cfg = GenericAPIModelConfig(name="test-env-missing", api_key=SecretStr(f"${env_name}"))
    result = cfg.get_api_keys()

    assert result == []
    # Verify the fake logger was used and warning was emitted with expected message
    assert hasattr(fake_get_logger, "logger")
    logger = fake_get_logger.logger
    assert logger.last_warning == f"Environment variable {env_name} not set"
    # Also verify get_logger was called with the expected arguments
    assert logger.init_args[0] == "swea-config"
    assert logger.init_kwargs.get("emoji") == "🔧"
