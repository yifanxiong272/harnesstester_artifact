# file: pr_agent/algo/ai_handlers/litellm_ai_handler.py:334-386
# asked: {"lines": [335, 337, 339, 340, 341, 342, 343, 344, 347, 350, 351, 352, 354, 356, 357, 358, 360, 361, 362, 363, 364, 365, 366, 367, 368, 371, 372, 373, 374, 375, 376, 377, 378, 384, 386], "branches": [[341, 342], [341, 343], [343, 344], [343, 347], [362, 363], [362, 371], [371, 372], [371, 384]]}
# gained: {"lines": [335, 337, 339, 340, 341, 342, 343, 344, 347, 350, 351, 352, 354, 356, 357, 358, 360, 361, 362, 363, 364, 365, 366, 367, 368, 371, 372, 373, 374, 375, 376, 377, 378, 384, 386], "branches": [[341, 342], [343, 344], [362, 363], [362, 371], [371, 372], [371, 384]]}

import types
import pytest

from pr_agent.algo.ai_handlers import litellm_ai_handler as mod


class _FakeLogger:
    def __init__(self, record):
        self._record = record
        self.add_called = False
        self.removed_ids = []

    def add(self, sink):
        # Simulate Loguru calling the sink with a message object that has .record
        class Message:
            pass

        msg = Message()
        msg.record = self._record
        # Call the sink to simulate capturing logs
        sink(msg)
        self.add_called = True
        return 12345

    def debug(self, *args, **kwargs):
        # no-op for debug
        pass

    def remove(self, handler_id):
        self.removed_ids.append(handler_id)


class _Cfg:
    def __init__(self, git_provider):
        self.git_provider = git_provider


class _Settings:
    def __init__(self, git_provider):
        self.config = _Cfg(git_provider)


@pytest.mark.parametrize(
    "success_cb,failure_cb,service_cb,command,pr_url,expect_trace,expect_run",
    [
        (["langfuse"], [], [], "cmd-fuse", "http://pr-fuse", True, False),
        ([], ["langsmith"], [], "cmd-smith", "http://pr-smith", False, True),
        (["langfuse"], [], ["langsmith"], "cmd-both", "http://pr-both", True, True),
    ],
)
def test_add_litellm_callbacks_various_callbacks(
    monkeypatch,
    success_cb,
    failure_cb,
    service_cb,
    command,
    pr_url,
    expect_trace,
    expect_run,
):
    """
    Test different combinations of litellm callbacks to ensure both 'langfuse'
    and 'langsmith' branches are exercised and metadata is built correctly.
    """

    # Prepare fake record that capture_logs expects
    record = {"extra": {"command": command, "pr_url": pr_url}}

    fake_logger = _FakeLogger(record)

    # Monkeypatch get_logger to return our fake logger
    monkeypatch.setattr(mod, "get_logger", lambda: fake_logger)

    # Monkeypatch get_settings to provide a known git_provider
    monkeypatch.setattr(mod, "get_settings", lambda: _Settings("github-test"))

    # Monkeypatch get_version to a known value
    monkeypatch.setattr(mod, "get_version", lambda: "9.9.9")

    # Ensure litellm callbacks are controllable lists
    # litellm is imported in the module; set attributes on that object
    monkeypatch.setattr(mod.litellm, "success_callback", success_cb, raising=False)
    monkeypatch.setattr(mod.litellm, "failure_callback", failure_cb, raising=False)
    monkeypatch.setattr(mod.litellm, "service_callback", service_cb, raising=False)

    # Create an instance without running any initializer (avoid side-effects)
    handler = object.__new__(mod.LiteLLMAIHandler)

    # Call the method under test
    inp = {}
    result = handler.add_litellm_callbacks(inp)

    # Basic structure checks
    assert "metadata" in result and isinstance(result["metadata"], dict)
    metadata = result["metadata"]

    # Verify trace (langfuse) expectations
    if expect_trace:
        assert metadata.get("trace_name") == command
        assert "trace_metadata" in metadata
        assert metadata["trace_metadata"].get("command") == command
        assert metadata["trace_metadata"].get("pr_url") == pr_url
    else:
        assert "trace_name" not in metadata
        assert "trace_metadata" not in metadata

    # Verify run (langsmith) expectations
    if expect_run:
        assert metadata.get("run_name") == command
        assert "extra" in metadata and isinstance(metadata["extra"], dict)
        assert metadata["extra"]["metadata"].get("command") == command
        assert metadata["extra"]["metadata"].get("pr_url") == pr_url
    else:
        assert "run_name" not in metadata
        assert "extra" not in metadata

    # Tags should exist if either callback present (since both branches add tags)
    if expect_trace or expect_run:
        tags = metadata.get("tags")
        assert isinstance(tags, list)
        # git_provider and version tag present
        assert "github-test" in tags
        assert f"version:{mod.get_version()}" in tags

    # Ensure our fake logger's add and remove were exercised
    assert fake_logger.add_called is True
    assert 12345 in fake_logger.removed_ids
