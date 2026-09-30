import types
import pytest
import asyncio

import pr_agent.tools.pr_line_questions as plq
from pr_agent.tools.pr_line_questions import PR_LineQuestions


class DummyGithubProvider:
    def __init__(self):
        self._published = []
        self._replies = []
        self._diff_files = []

    def publish_comment(self, text):
        # deterministic recording
        self._published.append(text)

    def reply_to_comment_from_comment_id(self, comment_id, text):
        self._replies.append((comment_id, text))

    def get_diff_files(self):
        # return whatever was configured for the test
        return list(self._diff_files)


class DummySettings:
    def __init__(self, pr_questions_use=False, get_map=None):
        self.pr_questions = types.SimpleNamespace(use_conversation_history=pr_questions_use)
        self._get_map = dict(get_map or {})

    def get(self, key, default=None):
        return self._get_map.get(key, default)


@pytest.mark.asyncio
async def test_ask_diff_publish_comment_round_050(monkeypatch):
    """
    Exercise branch where ask_diff is provided (lines 73-79),
    patch_with_lines is truthy (line 88), and publish_comment is used (line 99).
    Also verify sanitization of model answer that starts with "/" and contains "\n/".
    """
    # Prepare dummy environment
    dummy_provider = DummyGithubProvider()

    # make sure isinstance(provider, GithubProvider) works by patching the symbol
    monkeypatch.setattr(plq, "GithubProvider", DummyGithubProvider)

    # settings: ask_diff provided, others default/empty
    settings = DummySettings(pr_questions_use=False, get_map={
        'ask_diff_hunk': 'dummy-hunk',
        'line_start': '',
        'line_end': '',
        'side': 'RIGHT',
        'file_name': '',
        'comment_id': ''
    })
    monkeypatch.setattr(plq, 'get_settings', lambda: settings)

    # extract_hunk_lines_from_patch returns a non-empty patch (truthy)
    def fake_extract_hunk_lines_from_patch(patch, file_name, line_start=None, line_end=None, side=None):
        return ("/first_line\n/second_line", ['1', '2'])

    monkeypatch.setattr(plq, 'extract_hunk_lines_from_patch', fake_extract_hunk_lines_from_patch)

    # retry_with_fallback_models returns a coroutine that yields a string starting with '/'
    async def fake_retry_with_fallback_models(func, model_type=None):
        # starts with '/', and contains a newline followed by '/'
        return "/leading\n/next"

    monkeypatch.setattr(plq, 'retry_with_fallback_models', fake_retry_with_fallback_models)

    # silence logging
    monkeypatch.setattr(plq, 'get_logger', lambda: types.SimpleNamespace(info=lambda *a, **k: None))

    # Build PR_LineQuestions instance WITHOUT calling its real __init__ (avoid side effects)
    obj = object.__new__(PR_LineQuestions)
    obj.git_provider = dummy_provider
    obj.vars = {}
    # a minimal _load_conversation_history (not used in this test)
    obj._load_conversation_history = lambda: {'hist': []}
    obj._get_prediction = None

    # Call the async run method
    result = await obj.run()

    # Assertions / oracle
    # - run returns empty string
    assert result == ""
    # - patch_with_lines and selected_lines set from fake_extract_hunk_lines_from_patch
    assert getattr(obj, 'patch_with_lines') == "/first_line\n/second_line"
    assert getattr(obj, 'selected_lines') == ['1', '2']
    # - publish_comment should have been called once with sanitized text:
    #   original: "/leading\n/next"
    #   .strip() -> "/leading\n/next"
    #   replace("\n/","\n /") -> "/leading\n /next"
    #   startswith("/") -> True, so prefix with space -> " /leading\n /next"
    assert dummy_provider._published == [" /leading\n /next"]
    assert dummy_provider._replies == []


@pytest.mark.asyncio
async def test_no_ask_diff_reply_comment_and_conversation_history_round_050(monkeypatch):
    """
    Exercise branch where ask_diff is empty (line 80 -> 81),
    the for-loop inspects diff files and finds a matching filename (lines 82-87),
    conversation history is loaded (lines 62-64), and reply_to_comment_from_comment_id is used (lines 96-97).
    """
    dummy_provider = DummyGithubProvider()

    # ensure isinstance check succeeds
    monkeypatch.setattr(plq, "GithubProvider", DummyGithubProvider)

    # prepare a diff file-like object with filename and patch
    diff_file = types.SimpleNamespace(filename='target.py', patch='patch-for-target')
    dummy_provider._diff_files = [diff_file]

    # settings: no ask_diff_hunk, but set file_name and comment_id, enable conversation history
    settings = DummySettings(pr_questions_use=True, get_map={
        'ask_diff_hunk': '',
        'line_start': '',
        'line_end': '',
        'side': 'RIGHT',
        'file_name': 'target.py',
        'comment_id': '42'
    })
    monkeypatch.setattr(plq, 'get_settings', lambda: settings)

    # record that conversation history loader is called and returns something
    def fake_load_conversation_history():
        return {'loaded': True, 'messages': ['a']}

    # extract_hunk_lines_from_patch should be called with diff_file.patch
    def fake_extract_hunk_lines_from_patch(patch, file_name, line_start=None, line_end=None, side=None):
        assert patch == 'patch-for-target'
        assert file_name == 'target.py'
        return ('patchcontent2', ['100'])

    monkeypatch.setattr(plq, 'extract_hunk_lines_from_patch', fake_extract_hunk_lines_from_patch)

    # return an answer that includes a newline followed by '/', to assert the replace behavior
    async def fake_retry_with_fallback_models(func, model_type=None):
        return "answer\n/subloc"

    monkeypatch.setattr(plq, 'retry_with_fallback_models', fake_retry_with_fallback_models)
    monkeypatch.setattr(plq, 'get_logger', lambda: types.SimpleNamespace(info=lambda *a, **k: None))

    # Build instance without real __init__
    obj = object.__new__(PR_LineQuestions)
    obj.git_provider = dummy_provider
    obj.vars = {}
    obj._load_conversation_history = fake_load_conversation_history
    obj._get_prediction = None

    # Run
    result = await obj.run()

    # Assertions
    assert result == ""
    # conversation history must have been stored into vars
    assert obj.vars.get('conversation_history') == {'loaded': True, 'messages': ['a']}
    # patch and selected lines come from fake_extract_hunk_lines_from_patch
    assert getattr(obj, 'patch_with_lines') == 'patchcontent2'
    assert getattr(obj, 'selected_lines') == ['100']
    # reply_to_comment_from_comment_id should have been called with sanitized answer
    # original: "answer\n/subloc" -> replace -> "answer\n /subloc" -> does not start with '/', so no leading space
    assert dummy_provider._replies == [('42', 'answer\n /subloc')]
    assert dummy_provider._published == []
