import asyncio
from types import SimpleNamespace

from pr_agent.tools.pr_generate_labels import PRGenerateLabels
import pr_agent.tools.pr_generate_labels as mod


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class DummyGitProvider:
    def __init__(self, supported_get_labels=True, current_labels=None):
        self.published_comments = []
        self.published_labels = []
        self.removed_initial = False
        self._supported = supported_get_labels
        self._current_labels = current_labels or []

    def publish_comment(self, text, is_temporary=False):
        self.published_comments.append((text, is_temporary))

    def get_pr_labels(self):
        return list(self._current_labels)

    def is_supported(self, name):
        return self._supported

    def publish_labels(self, labels):
        self.published_labels.append(list(labels))

    def remove_initial_comment(self):
        self.removed_initial = True


async def _run_with_patched(mod_overrides, instance):
    """Helper to apply overrides (dict of name->value) on module, run instance.run(), and return result.
    Restores original attributes after running.
    """
    originals = {}
    for name, val in mod_overrides.items():
        originals[name] = getattr(mod, name)
        setattr(mod, name, val)
    try:
        return await instance.run()
    finally:
        for name, val in originals.items():
            setattr(mod, name, val)


def make_instance(pr_id="42"):
    # Create instance without invoking __init__ to avoid relying on internal constructor behavior
    inst = PRGenerateLabels.__new__(PRGenerateLabels)
    inst.pr_id = pr_id
    # placeholders for methods that run() will call
    async def noop_prepare_prediction(model):
        inst.prediction = True

    inst._prepare_prediction = noop_prepare_prediction

    def prepare_data():
        inst._prepared = True

    inst._prepare_data = prepare_data

    def prepare_labels():
        return getattr(inst, "_labels_to_return", [])

    inst._prepare_labels = prepare_labels

    # git_provider will be set per-test
    inst.git_provider = None

    return inst


def test_run_no_publish_round_064():
    """publish_output False: ensure run goes through prepare steps and does not call publish APIs."""
    inst = make_instance()
    inst._labels_to_return = ["auto"]
    inst._prepared = False

    # Dummy settings where publish_output is False
    settings = SimpleNamespace(config=SimpleNamespace(publish_output=False))
    logger = DummyLogger()

    async def retry_with_fallback_models(func):
        # call the provided coroutine-like prepare function with a dummy model
        await func(None)

    git = DummyGitProvider(supported_get_labels=True)
    inst.git_provider = git

    result = asyncio.run(_run_with_patched({
        "get_settings": lambda: settings,
        "get_logger": lambda: logger,
        "retry_with_fallback_models": retry_with_fallback_models,
        "get_user_labels": lambda labels: ["user_x"],
    }, inst))

    # publish_output False should skip publishing; prepare_data and prepare_labels should have run
    assert getattr(inst, "_prepared", False) is True
    assert git.published_comments == []
    assert git.published_labels == []
    assert git.removed_initial is False
    # When publish is False, final return value is an empty string per code flow
    assert result == ""


def test_run_publish_supported_round_064():
    """publish_output True and provider supports get_labels -> publish_labels should be called with merged labels."""
    inst = make_instance()
    inst._labels_to_return = ["auto1"]

    settings = SimpleNamespace(config=SimpleNamespace(publish_output=True))
    logger = DummyLogger()

    async def retry_with_fallback_models(func):
        await func(None)

    git = DummyGitProvider(supported_get_labels=True, current_labels=["existing1"])
    inst.git_provider = git

    def fake_get_user_labels(current):
        # verify it receives current labels from git provider and returns user labels
        assert current == ["existing1"]
        return ["user_label"]

    result = asyncio.run(_run_with_patched({
        "get_settings": lambda: settings,
        "get_logger": lambda: logger,
        "retry_with_fallback_models": retry_with_fallback_models,
        "get_user_labels": fake_get_user_labels,
    }, inst))

    # publish_labels should be called with auto labels + user labels
    assert git.published_labels == [["auto1", "user_label"]]
    assert git.removed_initial is True
    assert result == ""


def test_run_publish_unsupported_with_pr_labels_round_064():
    """publish_output True but provider doesn't support get_labels -> should publish comment with joined labels."""
    inst = make_instance()
    inst._labels_to_return = ["a", "b"]

    settings = SimpleNamespace(config=SimpleNamespace(publish_output=True))
    logger = DummyLogger()

    async def retry_with_fallback_models(func):
        await func(None)

    git = DummyGitProvider(supported_get_labels=False, current_labels=["c"])
    inst.git_provider = git

    def fake_get_user_labels(current):
        # return an empty list to ensure pr_labels stays as returned from _prepare_labels
        return []

    result = asyncio.run(_run_with_patched({
        "get_settings": lambda: settings,
        "get_logger": lambda: logger,
        "retry_with_fallback_models": retry_with_fallback_models,
        "get_user_labels": fake_get_user_labels,
    }, inst))

    # Expect a single non-temporary publish_comment with exact formatting
    expected_text = "## PR Labels:\n" + ", ".join(["a", "b"]) + "\n"
    assert (expected_text, False) in git.published_comments
    assert git.removed_initial is True
    assert result == ""


def test_run_prediction_false_round_064():
    """If prediction is falsy after preparation, run should return None early."""
    inst = make_instance()

    async def set_prediction_false(model):
        inst.prediction = False

    inst._prepare_prediction = set_prediction_false

    settings = SimpleNamespace(config=SimpleNamespace(publish_output=True))
    logger = DummyLogger()

    async def retry_with_fallback_models(func):
        await func(None)

    git = DummyGitProvider(supported_get_labels=True)
    inst.git_provider = git

    result = asyncio.run(_run_with_patched({
        "get_settings": lambda: settings,
        "get_logger": lambda: logger,
        "retry_with_fallback_models": retry_with_fallback_models,
        "get_user_labels": lambda labels: [],
    }, inst))

    assert result is None
    # No publishing should have occurred
    assert git.published_comments == []
    assert git.published_labels == []


def test_run_exception_logging_round_064():
    """If retry_with_fallback_models raises, the error is caught and logged."""
    inst = make_instance(pr_id="99")

    settings = SimpleNamespace(config=SimpleNamespace(publish_output=True))
    logger = DummyLogger()

    async def raiser(func):
        raise RuntimeError("boom")

    git = DummyGitProvider()
    inst.git_provider = git

    result = asyncio.run(_run_with_patched({
        "get_settings": lambda: settings,
        "get_logger": lambda: logger,
        "retry_with_fallback_models": raiser,
        "get_user_labels": lambda labels: [],
    }, inst))

    # The exception should be logged and the function returns an empty string at the end
    assert any("Error generating PR labels 99" in e for e in logger.errors)
    assert result == ""
