import types
import pytest

import sweagent.agent.reviewer as reviewer_mod


def test_chooser_init_round_098(monkeypatch):
    # Prepare sentinel return values and capture containers
    sentinel_model = object()
    sentinel_logger = object()
    called = {"get_model": False, "get_logger": False}
    captured = {}

    # Patch get_model to validate the shape of arguments passed from Chooser.__init__
    def fake_get_model(model_arg, tool_config_arg, *args, **kwargs):
        # Record that it was called
        called["get_model"] = True
        captured["model_arg"] = model_arg
        captured["tool_config"] = tool_config_arg

        # Ensure the second arg is the ToolConfig instance from the reviewer module
        assert isinstance(tool_config_arg, reviewer_mod.ToolConfig), (
            f"Expected ToolConfig instance, got: {type(tool_config_arg)}"
        )
        # Ensure the parse_function inside ToolConfig is an ActionParser instance
        assert hasattr(tool_config_arg, "parse_function"), "ToolConfig missing parse_function"
        assert isinstance(tool_config_arg.parse_function, reviewer_mod.ActionParser), (
            "parse_function is not an ActionParser instance"
        )
        return sentinel_model

    # Patch get_logger to validate name and emoji kwargs and return sentinel
    def fake_get_logger(name, *args, **kwargs):
        called["get_logger"] = True
        captured["logger_name"] = name
        captured["logger_kwargs"] = kwargs
        return sentinel_logger

    monkeypatch.setattr(reviewer_mod, "get_model", fake_get_model)
    monkeypatch.setattr(reviewer_mod, "get_logger", fake_get_logger)

    # Use a simple config-like object with the model attribute expected by Chooser.__init__
    config = types.SimpleNamespace(model="test-model-name")

    # Instantiate Chooser which should call our patched get_model and get_logger
    chooser = reviewer_mod.Chooser(config)

    # Assertions covering lines 294-296: config stored, model and logger set from patched functions
    assert chooser.config is config
    assert chooser.model is sentinel_model
    assert chooser.logger is sentinel_logger

    # Validate that get_model and get_logger were called exactly once (via flags)
    assert called["get_model"] is True
    assert called["get_logger"] is True

    # Validate the arguments passed into our get_model patch
    assert captured["model_arg"] == "test-model-name"
    # ToolConfig.parse_function should be an ActionParser instance
    tc = captured["tool_config"]
    assert isinstance(tc.parse_function, reviewer_mod.ActionParser)

    # Validate get_logger received the expected name and emoji shape
    assert captured["logger_name"] == "chooser"
    # Emoji in source is provided as the brain emoji — ensure it was passed through
    assert "emoji" in captured["logger_kwargs"]
    assert captured["logger_kwargs"]["emoji"] in ("\U0001F9E0", "🧠"), (
        "Expected brain emoji value for logger emoji kwarg"
    )
