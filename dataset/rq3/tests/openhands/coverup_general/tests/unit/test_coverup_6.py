# file: openhands/runtime/plugins/jupyter/execute_server.py:144-264
# asked: {"lines": [152, 153, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 181, 183, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 196, 197, 199, 200, 201, 204, 205, 206, 207, 208, 209, 210, 212, 213, 214, 215, 216, 219, 221, 222, 224, 225, 226, 228, 229, 230, 231, 232, 233, 234, 235, 237, 239, 240, 241, 242, 243, 246, 247, 249, 250, 251, 252, 253, 255, 256, 258, 261, 264], "branches": [[152, 153], [152, 155], [187, 188], [187, 226], [190, 191], [190, 192], [196, 197], [196, 199], [199, 200], [199, 204], [204, 205], [204, 208], [208, 209], [208, 212], [212, 213], [212, 224], [219, 187], [219, 221], [224, 187], [224, 225], [230, 231], [230, 232], [249, 250], [249, 255], [250, 251], [250, 252], [252, 249], [252, 253], [255, 256], [255, 258]]}
# gained: {"lines": [152, 153, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 167, 168, 169, 170, 171, 172, 173, 174, 176, 177, 181, 183, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 196, 199, 200, 201, 204, 208, 209, 210, 212, 213, 214, 215, 216, 219, 221, 222, 224, 225, 226, 228, 229, 230, 232, 233, 234, 235, 237, 239, 240, 241, 242, 243, 246, 247, 249, 250, 251, 252, 253, 255, 258, 261, 264], "branches": [[152, 153], [187, 188], [187, 226], [190, 191], [190, 192], [196, 199], [199, 200], [204, 208], [208, 209], [208, 212], [212, 213], [212, 224], [219, 221], [224, 225], [230, 232], [249, 250], [249, 255], [250, 251], [250, 252], [252, 253], [255, 258]]}

import asyncio
import os
import json
import types
import pytest

from tornado.escape import json_encode, json_decode

import openhands.runtime.plugins.jupyter.execute_server as es
from openhands.runtime.plugins.jupyter.execute_server import JupyterKernel


@pytest.mark.asyncio
async def test_execute_collects_text_and_image(monkeypatch):
    """
    Test that JupyterKernel.execute collects stream text, execute_result text/plain,
    and image/png into the returned structure.
    """

    # Prepare a fake websocket that captures the msg_id from write_message and then
    # returns messages that reference that parent msg_id.
    class FakeWS:
        def __init__(self, messages):
            self._messages = messages[:]  # copy
            self.stored_msg_id = None
            # stream.closed() should be False to represent an open connection after connect
            self.stream = types.SimpleNamespace(closed=lambda: False)

        async def write_message(self, message):
            # message is a JSON string - parse and capture msg_id
            d = json_decode(message)
            self.stored_msg_id = d["header"]["msg_id"]
            # return some response to be logged
            return "written"

        async def read_message(self):
            # Return messages one by one, filling in parent_header msg_id
            if not self._messages:
                # After messages exhausted, return None to simulate idle socket
                await asyncio.sleep(0)  # yield control
                return None
            msg = self._messages.pop(0)
            # Fill parent header with the stored msg_id if placeholder present
            if self.stored_msg_id is None:
                # No msg_id yet; wait a tiny bit for write_message to be called
                await asyncio.sleep(0)
            # Ensure parent_header msg_id matches stored
            msg["parent_header"] = {"msg_id": self.stored_msg_id}
            return json_encode(msg)

    # Messages to be returned by read_message
    messages = [
        {"msg_type": "stream", "content": {"text": "hello\n"}},
        {
            "msg_type": "execute_result",
            "content": {"data": {"text/plain": ">>> result\n", "image/png": "R0lGODdhAQABAIAAAP"}}},
        {"msg_type": "execute_reply", "content": {}},
    ]
    fake_ws = FakeWS(messages)

    # Instantiate kernel and monkeypatch its _connect to set our fake_ws
    kernel = JupyterKernel("localhost:8888", "conv-1")
    async def fake_connect():
        kernel.ws = fake_ws
        # set a kernel id too (not used in this test)
        kernel.kernel_id = "k-1"
    monkeypatch.setattr(kernel, "_connect", fake_connect)

    # Ensure DEBUG env var is set to exercise the logging branch
    monkeypatch.setenv("DEBUG", "1")

    result = await kernel.execute("print('hi')", timeout=5)

    # Validate returned structure
    assert isinstance(result, dict)
    assert "text" in result and "images" in result
    # The text outputs should include both the stream text and the execute_result text
    assert "hello" in result["text"]
    assert ">>> result" in result["text"]
    # The image should have been converted to a data URL
    assert len(result["images"]) == 1
    assert result["images"][0].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_execute_timeout_triggers_interrupt(monkeypatch):
    """
    Test that a timeout in execute triggers interrupt_kernel, which calls AsyncHTTPClient.fetch.
    """

    # Fake websocket where read_message will never return a message with matching parent id,
    # causing the wait_for_messages to hang until timeout.
    class HangingWS:
        def __init__(self):
            self.stream = types.SimpleNamespace(closed=lambda: False)
            self.stored_msg_id = None

        async def write_message(self, message):
            d = json_decode(message)
            self.stored_msg_id = d["header"]["msg_id"]
            return "written"

        async def read_message(self):
            # Always return None (no messages) to force waiting/timing out
            await asyncio.sleep(0)
            return None

    fake_ws = HangingWS()

    kernel = JupyterKernel("localhost:8888", "conv-2")

    # Make _connect assign our hanging ws
    async def fake_connect():
        kernel.ws = fake_ws
    monkeypatch.setattr(kernel, "_connect", fake_connect)

    # Ensure kernel_id is set so interrupt_kernel will attempt to call the API
    kernel.kernel_id = "kernel-to-interrupt"

    # Prepare a fake AsyncHTTPClient.fetch to record that it was called and to return a dummy response
    called = {}
    class FakeResponse:
        def __init__(self, url):
            self.url = url
        def __repr__(self):
            return f"<FakeResponse {self.url}>"

    class FakeHTTPClient:
        async def fetch(self, url, method="GET", body=None):
            # Record call
            called["url"] = url
            called["method"] = method
            called["body"] = body
            return FakeResponse(url)

    # Monkeypatch the AsyncHTTPClient in the module namespace used by interrupt_kernel
    monkeypatch.setattr(es, "AsyncHTTPClient", FakeHTTPClient)

    # Run execute with a short timeout to trigger asyncio.TimeoutError and thus interrupt_kernel
    result = await kernel.execute("while True: pass", timeout=0.05)

    # Validate that the interrupt was attempted
    assert "url" in called
    assert kernel.kernel_id in called["url"]
    assert called["method"] == "POST"
    # Body should be JSON encoded with kernel_id
    body_decoded = json_decode(called["body"])
    assert body_decoded.get("kernel_id") == kernel.kernel_id

    # Validate returned timeout message
    assert isinstance(result, dict)
    assert result["images"] == []
    assert "[Execution timed out" in result["text"]
