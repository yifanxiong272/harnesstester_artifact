# file: aider/coders/base_coder.py:1340-1394
# asked: {"lines": [1343, 1344, 1345, 1346, 1348, 1349, 1350, 1351, 1352, 1354, 1355, 1357, 1358, 1359, 1360, 1361, 1362, 1363, 1364, 1366, 1367, 1369, 1370, 1372, 1373, 1374, 1375, 1376, 1377, 1379, 1380, 1381, 1383, 1384, 1385, 1387, 1388, 1390, 1391, 1392, 1394], "branches": [[1341, 1343], [1343, 1344], [1343, 1345], [1345, 1346], [1345, 1348], [1354, 1355], [1354, 1357], [1358, 0], [1358, 1359], [1360, 1361], [1360, 1362], [1363, 1364], [1363, 1366], [1387, 1358], [1387, 1388]]}
# gained: {"lines": [1343, 1345, 1348, 1349, 1350, 1351, 1352, 1354, 1357, 1358, 1359, 1360, 1362, 1363, 1366, 1367, 1369, 1370, 1372, 1373, 1374, 1375, 1376, 1377, 1379, 1380, 1381, 1383, 1384, 1387, 1388, 1390, 1391, 1392, 1394], "branches": [[1341, 1343], [1343, 1345], [1345, 1348], [1354, 1357], [1358, 0], [1358, 1359], [1360, 1362], [1363, 1366], [1387, 1388]]}

import time
import threading
import pytest

from aider.coders.base_coder import Coder
from aider import llm as llm_module


class DummyIO:
    def __init__(self):
        self.warnings = []
        self.outputs = []
        self.pretty = False
        self.chat_history_file = "unused"
        self.encoding = "utf-8"

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def read_text(self, path):
        return ""


class DummyChunks:
    def cacheable_messages(self):
        return [{"role": "user", "content": "hello"}]


class DummyModel:
    def __init__(self, name="m"):
        self.name = name
        self.extra_params = {}
        self.reasoning_tag = None
        self.streaming = True
        self.cache_control = True
        self.info = {"max_input_tokens": 0}
        self.weak_model = self
        self.max_chat_history_tokens = 0

    def commit_message_models(self):
        return []


class FakeTimer:
    """
    Replacement for threading.Timer that runs the target synchronously when start() is called.
    The daemon attribute is supported for compatibility.
    """

    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.daemon = False

    def start(self):
        # Call the function synchronously to avoid background threads in tests
        self.function(*self.args, **self.kwargs)

    def cancel(self):
        pass


def make_coder():
    main_model = DummyModel()
    io = DummyIO()
    # pass summarizer and use_git=False to avoid heavy initialization paths
    coder = Coder(main_model=main_model, io=io, summarizer=object(), use_git=False)
    # ensure consistent state used by warm_cache
    coder.add_cache_headers = True
    coder.num_cache_warming_pings = 1
    coder.ok_to_warm_cache = True
    coder.cache_warming_thread = None
    coder.verbose = False
    return coder


def test_warm_cache_handles_completion_exception(monkeypatch):
    monkeypatch.setenv("AIDER_CACHE_KEEPALIVE_DELAY", "0")
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(threading, "Timer", FakeTimer)

    coder = make_coder()
    chunks = DummyChunks()

    def fake_completion_raise(*_, **__):
        # Ensure the worker loop will exit after this exception
        coder.ok_to_warm_cache = False
        raise RuntimeError("simulated LLM failure")

    monkeypatch.setattr(llm_module.litellm, "completion", fake_completion_raise)

    returned = coder.warm_cache(chunks)

    assert returned is chunks
    assert any("Cache warming error" in w for w in coder.io.warnings)


def test_warm_cache_successful_completion_and_verbose_output(monkeypatch):
    monkeypatch.setenv("AIDER_CACHE_KEEPALIVE_DELAY", "0")
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(threading, "Timer", FakeTimer)

    coder = make_coder()
    coder.verbose = True
    chunks = DummyChunks()

    class Usage1:
        prompt_cache_hit_tokens = 5

    class Completion1:
        usage = Usage1()

    class Usage2:
        prompt_cache_hit_tokens = 0
        cache_read_input_tokens = 7

    class Completion2:
        usage = Usage2()

    calls = {"n": 0}

    def fake_completion_return(*_, **__):
        # stop the loop after the first successful return to avoid infinite looping
        coder.ok_to_warm_cache = False
        calls["n"] += 1
        if calls["n"] == 1:
            return Completion1()
        return Completion2()

    monkeypatch.setattr(llm_module.litellm, "completion", fake_completion_return)

    returned = coder.warm_cache(chunks)

    assert returned is chunks
    assert any("Warmed" in o for o in coder.io.outputs)
    # ensure numeric token counts are present in output (formatted)
    assert any("5" in o or "7" in o for o in coder.io.outputs)
