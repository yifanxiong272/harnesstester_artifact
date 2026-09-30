import sys
import types
import asyncio
from typing import Any

import importlib

import gpt_researcher.mcp.streaming as streaming_module
from gpt_researcher.mcp.streaming import MCPStreamer


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg: Any, *args, **kwargs):
        # Normalize to str to make assertions simple and deterministic
        self.infos.append(str(msg))

    def error(self, msg: Any, *args, **kwargs):
        self.errors.append(str(msg))


def _make_utils_module(stream_output_coro):
    mod = types.ModuleType("gpt_researcher.actions.utils")
    mod.stream_output = stream_output_coro
    return mod


def test_no_websocket_stream_log_round_138():
    """When websocket is falsy, stream_output should not be called and only logger.info is used."""
    fake_logger = FakeLogger()
    # patch the module-level logger used by the implementation
    orig_logger = getattr(streaming_module, "logger", None)
    streaming_module.logger = fake_logger

    try:
        s = MCPStreamer(websocket=None)
        # call the async method synchronously for pytest determinism
        asyncio.run(s.stream_log("hello-no-ws", data={"k": "v"}))

        assert fake_logger.infos == ["hello-no-ws"]
        assert fake_logger.errors == []
    finally:
        # restore original logger
        if orig_logger is None:
            delattr(streaming_module, "logger")
        else:
            streaming_module.logger = orig_logger


def test_with_websocket_success_stream_log_round_138():
    """When websocket is present, stream_output is awaited with correct payload.

    This patches the import target gpt_researcher.actions.utils.stream_output so the
    in-function relative import resolves to our stub without network calls.
    """
    fake_logger = FakeLogger()
    orig_logger = getattr(streaming_module, "logger", None)
    streaming_module.logger = fake_logger

    captured = {}

    async def fake_stream_output(*, type, content, output, websocket, metadata):
        # store received values for assertion
        captured["type"] = type
        captured["content"] = content
        captured["output"] = output
        captured["websocket"] = websocket
        captured["metadata"] = metadata
        # mimic an async function that completes successfully
        return {"status": "ok"}

    utils_mod = _make_utils_module(fake_stream_output)
    # inject into sys.modules so the relative import inside the function finds it
    sys_modules_key = "gpt_researcher.actions.utils"
    prev = sys.modules.get(sys_modules_key)
    sys.modules[sys_modules_key] = utils_mod

    try:
        ws_obj = object()
        s = MCPStreamer(websocket=ws_obj)
        asyncio.run(s.stream_log("hello-ws", data={"x": 1}))

        # logger.info should still be called with the original message
        assert fake_logger.infos == ["hello-ws"]
        assert fake_logger.errors == []

        # ensure stream_output was invoked with exact expected keyword payload
        assert captured["type"] == "logs"
        assert captured["content"] == "mcp_retriever"
        assert captured["output"] == "hello-ws"
        assert captured["websocket"] is ws_obj
        assert captured["metadata"] == {"x": 1}
    finally:
        # cleanup injected module and logger
        if prev is None:
            del sys.modules[sys_modules_key]
        else:
            sys.modules[sys_modules_key] = prev
        if orig_logger is None:
            delattr(streaming_module, "logger")
        else:
            streaming_module.logger = orig_logger


def test_with_websocket_exception_stream_log_round_138():
    """If the injected stream_output raises, the exception is caught and logged as error."""
    fake_logger = FakeLogger()
    orig_logger = getattr(streaming_module, "logger", None)
    streaming_module.logger = fake_logger

    async def raising_stream_output(*, type, content, output, websocket, metadata):
        raise RuntimeError("boom")

    utils_mod = _make_utils_module(raising_stream_output)
    sys_modules_key = "gpt_researcher.actions.utils"
    prev = sys.modules.get(sys_modules_key)
    sys.modules[sys_modules_key] = utils_mod

    try:
        ws = object()
        s = MCPStreamer(websocket=ws)
        asyncio.run(s.stream_log("will-raise", data=None))

        # info was still called prior to attempting the stream
        assert fake_logger.infos == ["will-raise"]
        # error should contain the raised exception message
        assert any("boom" in e for e in fake_logger.errors), f"errors: {fake_logger.errors}"
    finally:
        if prev is None:
            del sys.modules[sys_modules_key]
        else:
            sys.modules[sys_modules_key] = prev
        if orig_logger is None:
            delattr(streaming_module, "logger")
        else:
            streaming_module.logger = orig_logger
