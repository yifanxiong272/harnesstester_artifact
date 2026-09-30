import importlib
import types
from types import SimpleNamespace

import pytest

# Import the module under test
module_path = 'pr_agent.algo.ai_handlers.litellm_ai_handler'
target = importlib.import_module(module_path)


class FakeLogger:
    def __init__(self, message):
        self._message = message
        self.removed = False
        self.added_handlers = []

    def add(self, sink):
        # Immediately invoke the sink with the prepared message to simulate Loguru calling it
        sink(self._message)
        handler_id = 123
        self.added_handlers.append((handler_id, sink))
        return handler_id

    def debug(self, *args, **kwargs):
        # no-op for deterministic tests
        return None

    def remove(self, handler_id):
        self.removed = True
        return None


class DummySettings:
    def __init__(self, git_provider="github"):
        cfg = SimpleNamespace()
        cfg.git_provider = git_provider
        self.config = cfg


def _call_add_callbacks_with_record(record, litellm_callbacks, monkeypatch):
    """
    Helper that patches the module-level dependencies and calls the function under test.
    Returns the mutated kwargs returned by the function.
    """
    # Prepare a fake message object with a .record attribute
    message = SimpleNamespace(record=record)

    # Fake get_logger that returns a FakeLogger bound to our message
    def fake_get_logger():
        return FakeLogger(message)

    monkeypatch.setattr(target, 'get_logger', fake_get_logger)

    # Fake settings with a stable git_provider
    monkeypatch.setattr(target, 'get_settings', lambda: DummySettings(git_provider='git-provider-x'))

    # Fake version
    monkeypatch.setattr(target, 'get_version', lambda: '0.0.test')

    # Patch litellm callbacks on the module to control which callbacks are present
    litellm_obj = types.SimpleNamespace(
        success_callback=litellm_callbacks.get('success_callback', []),
        failure_callback=litellm_callbacks.get('failure_callback', []),
        service_callback=litellm_callbacks.get('service_callback', []),
    )
    monkeypatch.setattr(target, 'litellm', litellm_obj)

    # Prepare kwargs to be passed in and mutated
    kwargs = {}

    # Call the function under test. It's an instance method but doesn't use self, so pass None.
    result = target.LiteLLMAIHandler.add_litellm_callbacks(None, kwargs)
    return result


def test_add_litellm_callbacks_sets_langfuse_metadata_round_071(monkeypatch):
    # Record contains both command and pr_url so both branches inside capture_logs execute
    record = {'extra': {'command': 'run-tests', 'pr_url': 'http://example/pr/1'}}

    litellm_callbacks = {
        'success_callback': ['langfuse'],
        'failure_callback': [],
        'service_callback': []
    }

    result_kwargs = _call_add_callbacks_with_record(record, litellm_callbacks, monkeypatch)

    # Validate that metadata for langfuse was added
    metadata = result_kwargs.get('metadata')
    assert isinstance(metadata, dict)
    # trace_name should be the captured command
    assert metadata.get('trace_name') == 'run-tests'
    # tags should include git provider, command, and version string
    tags = metadata.get('tags')
    assert isinstance(tags, list)
    assert 'git-provider-x' in tags
    assert 'run-tests' in tags
    assert any(str(t).startswith('version:') for t in tags)
    # trace_metadata should include both command and pr_url
    trace_metadata = metadata.get('trace_metadata')
    assert trace_metadata == {'command': 'run-tests', 'pr_url': 'http://example/pr/1'}


def test_add_litellm_callbacks_sets_langsmith_metadata_round_071(monkeypatch):
    # Record contains both command and pr_url so capture_logs will include both into captured_extra
    record = {'extra': {'command': 'deploy', 'pr_url': 'http://example/pr/2'}}

    litellm_callbacks = {
        'success_callback': [],
        'failure_callback': [],
        'service_callback': ['langsmith']
    }

    result_kwargs = _call_add_callbacks_with_record(record, litellm_callbacks, monkeypatch)

    metadata = result_kwargs.get('metadata')
    assert isinstance(metadata, dict)
    # run_name should be the captured command
    assert metadata.get('run_name') == 'deploy'
    # tags should include git provider, command, and version string
    tags = metadata.get('tags')
    assert isinstance(tags, list)
    assert 'git-provider-x' in tags
    assert 'deploy' in tags
    assert any(str(t).startswith('version:') for t in tags)
    # extra.metadata should contain the command and pr_url
    extra = metadata.get('extra')
    assert isinstance(extra, dict)
    assert extra.get('metadata') == {'command': 'deploy', 'pr_url': 'http://example/pr/2'}


def test_add_litellm_callbacks_handles_missing_command_but_prurl_round_071(monkeypatch):
    # Record where 'command' is missing but 'pr_url' exists exercises the branch
    # where the first conditional for command is false and the pr_url conditional is true.
    record = {'extra': {'pr_url': 'http://example/pr/3'}}

    litellm_callbacks = {
        'success_callback': [],
        'failure_callback': [],
        'service_callback': []
    }

    result_kwargs = _call_add_callbacks_with_record(record, litellm_callbacks, monkeypatch)

    # No callbacks trigger metadata population, so metadata should be an empty dict
    metadata = result_kwargs.get('metadata')
    assert metadata == {}

    # Ensure function did not raise and returned the same kwargs mapping
    assert isinstance(result_kwargs, dict)
