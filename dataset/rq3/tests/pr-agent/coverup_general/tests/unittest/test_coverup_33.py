# file: pr_agent/tools/pr_generate_labels.py:65-102
# asked: {"lines": [70, 71, 72, 73, 75, 77, 78, 79, 81, 83, 85, 86, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 102], "branches": [[72, 73], [72, 75], [78, 79], [78, 81], [85, 86], [85, 102], [92, 93], [92, 94], [94, 95], [94, 98]]}
# gained: {"lines": [70, 71, 72, 73, 75, 77, 78, 79, 83, 85, 86, 88, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 102], "branches": [[72, 73], [78, 79], [85, 86], [92, 93], [92, 94], [94, 95]]}

import asyncio
import types
import importlib
import pytest

module = importlib.import_module("pr_agent.tools.pr_generate_labels")


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class DummyAIHandler:
    def __init__(self):
        self.main_pr_language = None


class DummyTokenHandler:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class FakeGitProvider:
    def __init__(self, *, support_get_labels=True, initial_labels=None):
        self._support_get_labels = support_get_labels
        self._initial_labels = list(initial_labels or [])
        self.published_comments = []
        self.published_labels = None
        self.removed_initial_comment = False
        self.pr = types.SimpleNamespace(title="PR Title")

    def get_languages(self):
        return []

    def get_files(self):
        return []

    def get_pr_id(self):
        return 42

    def get_pr_branch(self):
        return "feature/branch"

    def get_pr_description(self, full=False):
        return "short description" if not full else "full description"

    def get_commit_messages(self):
        return "commit1\ncommit2"

    def publish_comment(self, text, is_temporary=True):
        self.published_comments.append((text, is_temporary))

    def get_pr_labels(self):
        return list(self._initial_labels)

    def is_supported(self, name):
        if name == "get_labels":
            return self._support_get_labels
        return False

    def publish_labels(self, labels):
        self.published_labels = list(labels)

    def remove_initial_comment(self):
        self.removed_initial_comment = True


class DummySettings:
    def __init__(self, publish_output=True, enable_custom_labels=False, extra_instructions=""):
        self.config = types.SimpleNamespace(publish_output=publish_output, enable_custom_labels=enable_custom_labels)
        self.pr_description = types.SimpleNamespace(extra_instructions=extra_instructions)
        self.pr_custom_labels_prompt = types.SimpleNamespace(system="sys", user="user")


@pytest.mark.parametrize("support_get_labels, initial_labels, expected_published_labels", [
    (True, ["userlab"], ["label1", "userlab"]),
    (False, [], None),
])
def test_run_publish_branches(monkeypatch, support_get_labels, initial_labels, expected_published_labels):
    fake_logger = DummyLogger()
    monkeypatch.setattr(module, "get_logger", lambda: fake_logger)

    fake_settings = DummySettings(publish_output=True)
    monkeypatch.setattr(module, "get_settings", lambda: fake_settings)

    monkeypatch.setattr(module, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(module, "get_main_pr_language", lambda languages, files: "py")

    provider = FakeGitProvider(support_get_labels=support_get_labels, initial_labels=initial_labels)
    # get_git_provider should return a callable that when called with pr_url returns provider
    monkeypatch.setattr(module, "get_git_provider", lambda: (lambda pr_url: provider))

    monkeypatch.setattr(module, "get_user_labels", lambda labels: list(labels))

    async def fake_retry(func):
        # call the provided coroutine-like function with a model name
        await func("modelX")

    monkeypatch.setattr(module, "retry_with_fallback_models", fake_retry)

    prg = module.PRGenerateLabels("http://example/pr/1", ai_handler=lambda: DummyAIHandler())

    # Define a fake prepare_prediction coroutine that uses the prg closure (no binding)
    async def fake_prepare_prediction(model):
        # set prediction on the outer prg instance
        prg.prediction = "some prediction"

    # Assign the coroutine function directly (not as a bound method) so fake_retry can call it with one arg
    prg._prepare_prediction = fake_prepare_prediction

    # Prepare a no-op prepare_data function (no args)
    def fake_prepare_data():
        return None

    prg._prepare_data = fake_prepare_data

    # prepare labels based on param
    if support_get_labels:
        def fake_prepare_labels():
            return ["label1"]
    else:
        def fake_prepare_labels():
            return ["labelA"]

    prg._prepare_labels = fake_prepare_labels

    result = asyncio.run(prg.run())

    assert result == ""

    # Logger should have recorded generating info
    assert any("Generating a PR labels" in m for m in fake_logger.infos)

    # Initial preparing comment must have been posted
    assert provider.published_comments, "Expected at least one published comment"
    assert provider.published_comments[0][0] == "Preparing PR labels..."
    assert provider.published_comments[0][1] is True

    if support_get_labels:
        assert provider.published_labels == expected_published_labels
        assert provider.removed_initial_comment is True
    else:
        assert provider.published_labels is None
        # fallback comment should be present
        assert any(text.startswith("## PR Labels:") and is_temp is False for text, is_temp in provider.published_comments)
        assert provider.removed_initial_comment is True


def test_run_exception_path(monkeypatch):
    fake_logger = DummyLogger()
    monkeypatch.setattr(module, "get_logger", lambda: fake_logger)

    fake_settings = DummySettings(publish_output=True)
    monkeypatch.setattr(module, "get_settings", lambda: fake_settings)

    monkeypatch.setattr(module, "TokenHandler", DummyTokenHandler)
    monkeypatch.setattr(module, "get_main_pr_language", lambda languages, files: "py")

    provider = FakeGitProvider()
    monkeypatch.setattr(module, "get_git_provider", lambda: (lambda pr_url: provider))

    # Make retry raise to trigger exception handling
    async def retry_raises(func):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(module, "retry_with_fallback_models", retry_raises)

    prg = module.PRGenerateLabels("http://example/pr/2", ai_handler=lambda: DummyAIHandler())

    result = asyncio.run(prg.run())
    assert result == ""
    assert any("Error generating PR labels" in e for e in fake_logger.errors)
