# file: aider/coders/base_coder.py:1024-1034
# asked: {"lines": [1028, 1029, 1031, 1032, 1033, 1034], "branches": [[1025, 1028], [1031, 1032], [1031, 1033]]}
# gained: {"lines": [1028, 1029, 1031, 1032, 1033, 1034], "branches": [[1025, 1028], [1031, 1032], [1031, 1033]]}

import pytest

import aider.coders.base_coder as base_coder
from aider.coders.base_coder import Coder


class DummyThread:
    def __init__(self):
        self.join_called = False

    def join(self):
        self.join_called = True


class DummyAnalytics:
    def __init__(self):
        self.event = lambda *a, **k: None


class DummyCommands:
    def __init__(self, io, coder):
        self.io = io
        self.coder = coder


class DummyLinter:
    def __init__(self, root=None, encoding=None):
        self.root = root
        self.encoding = encoding


class DummyChatSummary:
    def __init__(self, models, max_tokens):
        self.models = models
        self.max_tokens = max_tokens


class DummyRepoMap:
    def __init__(self, *args, **kwargs):
        pass


class DummyGitRepo:
    def __init__(self, *args, **kwargs):
        raise FileNotFoundError


class DummyIO:
    def __init__(self):
        self.pretty = False
        self.encoding = "utf-8"
        self.chat_history_file = "history.md"

    def read_text(self, path):
        return ""

    def tool_warning(self, msg):
        # keep a record if needed
        self._last_warning = msg

    def tool_output(self, msg):
        self._last_output = msg


class DummyModel:
    def __init__(self):
        self.reasoning_tag = None
        self.streaming = True
        self.cache_control = False
        self.info = {}
        self.weak_model = object()
        self.max_chat_history_tokens = 100
        self.use_repo_map = False

    def commit_message_models(self):
        return []


@pytest.fixture(autouse=True)
def patch_base_coder(monkeypatch):
    # Monkeypatch classes in base_coder to lightweight dummies to avoid side effects
    monkeypatch.setattr(base_coder, "Analytics", DummyAnalytics)
    monkeypatch.setattr(base_coder, "Commands", DummyCommands)
    monkeypatch.setattr(base_coder, "Linter", DummyLinter)
    monkeypatch.setattr(base_coder, "ChatSummary", DummyChatSummary)
    monkeypatch.setattr(base_coder, "RepoMap", DummyRepoMap)
    monkeypatch.setattr(base_coder, "GitRepo", DummyGitRepo)
    yield


def test_summarize_end_when_summarizing_equals_done_messages():
    io = DummyIO()
    model = DummyModel()
    # create coder with patched dependencies; disable git to avoid GitRepo usage
    coder = Coder(main_model=model, io=io, use_git=False)

    # prepare dummy thread and message lists
    thread = DummyThread()
    coder.summarizer_thread = thread

    shared_messages = ["m1", "m2"]
    coder.summarizing_messages = shared_messages
    coder.done_messages = shared_messages

    prev_summarized = ["done1"]
    coder.summarized_done_messages = prev_summarized

    # sanity preconditions
    assert coder.summarizer_thread is thread
    assert coder.summarizing_messages is coder.done_messages
    assert coder.summarized_done_messages is prev_summarized

    # call method under test
    coder.summarize_end()

    # join must have been called on the thread
    assert thread.join_called is True

    # summarizer_thread cleared
    assert coder.summarizer_thread is None

    # when summarizing_messages == done_messages, done_messages should be replaced
    # by the previous summarized_done_messages object
    assert coder.done_messages is prev_summarized

    # summarizing_messages should be cleared
    assert coder.summarizing_messages is None

    # summarized_done_messages reset to a new empty list
    assert coder.summarized_done_messages == []
    assert isinstance(coder.summarized_done_messages, list)


def test_summarize_end_when_summarizing_differs_from_done_messages():
    io = DummyIO()
    model = DummyModel()
    coder = Coder(main_model=model, io=io, use_git=False)

    # prepare dummy thread and different message lists
    thread = DummyThread()
    coder.summarizer_thread = thread

    coder.summarizing_messages = ["a"]
    original_done = ["orig"]
    coder.done_messages = original_done

    coder.summarized_done_messages = ["to_replace"]

    # sanity preconditions
    assert coder.summarizer_thread is thread
    assert coder.summarizing_messages is not coder.done_messages

    # call method under test
    coder.summarize_end()

    # join must have been called on the thread
    assert thread.join_called is True

    # summarizer_thread cleared
    assert coder.summarizer_thread is None

    # done_messages should remain unchanged because summarizing_messages != done_messages
    assert coder.done_messages is original_done

    # summarizing_messages should be cleared
    assert coder.summarizing_messages is None

    # summarized_done_messages reset to empty list
    assert coder.summarized_done_messages == []
