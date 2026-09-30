import asyncio
import pytest

import pr_agent.tools.pr_line_questions as plq
from pr_agent.tools.pr_line_questions import PR_LineQuestions


class DummyGitProviderForComment:
    def __init__(self):
        self.replied = None
        self.published = None

    def reply_to_comment_from_comment_id(self, comment_id, body):
        # record call
        self.replied = (comment_id, body)

    def publish_comment(self, body):
        self.published = body

    def get_diff_files(self):
        # default: no files
        return []


class DummyDiffFile:
    def __init__(self, filename, patch):
        self.filename = filename
        self.patch = patch


class FakePRQuestions:
    def __init__(self, use_conv):
        self.use_conversation_history = use_conv


class FakeSettings:
    def __init__(self, mapping, use_conv=False):
        self._mapping = dict(mapping)
        self.pr_questions = FakePRQuestions(use_conv)

    def get(self, key, default=None):
        return self._mapping.get(key, default)


@pytest.mark.asyncio
async def test_run_with_ask_diff_and_comment_id_round_050(monkeypatch):
    """
    - exercise path where ask_diff is present (lines ~73-79),
      extract_hunk_lines_from_patch is used, patch_with_lines is truthy,
      retry_with_fallback_models returns an answer that starts with '/'
      and contains a '\n/' to trigger both sanitization branches (lines ~91-93),
      and comment_id is set so reply_to_comment_from_comment_id is called (lines ~96-97).
    """
    # patch get_settings in the module to provide ask_diff and comment_id
    fake_settings = FakeSettings({
        'ask_diff_hunk': 'SOME_HUNK',
        'line_start': '',
        'line_end': '',
        'side': 'RIGHT',
        'file_name': '',
        'comment_id': 'c123'
    }, use_conv=False)
    monkeypatch.setattr(plq, 'get_settings', lambda: fake_settings)

    # patch extract_hunk_lines_from_patch to return non-empty patch_with_lines
    def fake_extract(hunk_or_patch, filename, line_start=None, line_end=None, side=None):
        return ("+++ patched lines +++", [1, 2])

    monkeypatch.setattr(plq, 'extract_hunk_lines_from_patch', fake_extract)

    # patch retry_with_fallback_models to be an async function returning a string
    async def fake_retry(func, model_type=None):
        # produce an answer that starts with '/' and contains a '\n/' to be sanitized
        await asyncio.sleep(0)  # keep it async but immediate
        return "/hello\n/world"

    monkeypatch.setattr(plq, 'retry_with_fallback_models', fake_retry)

    # create instance without running __init__ and configure required attributes
    inst = object.__new__(PR_LineQuestions)
    git = DummyGitProviderForComment()
    inst.git_provider = git
    inst.vars = {}
    # _load_conversation_history should not be called in this scenario, but provide safe stub
    inst._load_conversation_history = lambda: ["noop"]
    # _get_prediction exists but our fake_retry ignores it, provide a coroutine stub
    async def _get_prediction_stub(model):
        return "unused"
    inst._get_prediction = _get_prediction_stub

    # run and assert
    result = await PR_LineQuestions.run(inst)

    assert result == ""
    # reply_to_comment_from_comment_id must have been called with sanitized content
    # original returned "/hello\n/world" -> strip() same -> replace "\n/" -> "\n /" -> then startswith('/')-> prepend space
    assert git.replied is not None
    comment_id, body = git.replied
    assert comment_id == 'c123'
    assert body == " /hello\n /world"


@pytest.mark.asyncio
async def test_run_with_diff_files_no_comment_round_050(monkeypatch):
    """
    - exercise path where ask_diff is empty and diff_files are iterated (lines ~80-87),
      matching file.filename triggers extract_hunk_lines_from_patch, patch_with_lines truthy,
      conversation history branch is exercised (lines ~62-64),
      and publish_comment is called when comment_id is empty (lines ~96-99).
    """
    # prepare settings: no ask_diff, file_name 'target.py', no comment_id
    fake_settings = FakeSettings({
        'ask_diff_hunk': '',
        'line_start': 10,
        'line_end': 20,
        'side': 'RIGHT',
        'file_name': 'target.py',
        'comment_id': ''
    }, use_conv=True)
    monkeypatch.setattr(plq, 'get_settings', lambda: fake_settings)

    # patch GithubProvider class in the module so isinstance check will pass
    class FakeGithubProvider:
        pass

    monkeypatch.setattr(plq, 'GithubProvider', FakeGithubProvider)

    # prepare a git provider instance that returns a diff file matching 'target.py'
    class GP:
        def __init__(self):
            self.published = None

        def get_diff_files(self):
            return [DummyDiffFile('other.py', 'patch1'), DummyDiffFile('target.py', 'PATCH_CONTENT')]

        def publish_comment(self, body):
            self.published = body

        def reply_to_comment_from_comment_id(self, comment_id, body):
            # not expected to be called
            raise AssertionError("reply_to_comment_from_comment_id should not be called in this test")

    git = GP()

    # patch extract_hunk_lines_from_patch to return something truthy for the matched file
    def fake_extract_from_patch(patch, filename, line_start=None, line_end=None, side=None):
        # ensure args passed are as expected
        assert filename == 'target.py'
        assert patch == 'PATCH_CONTENT'
        return ("LINES", [line_start, line_end])

    monkeypatch.setattr(plq, 'extract_hunk_lines_from_patch', fake_extract_from_patch)

    # patch retry_with_fallback_models to return an answer that does not start with '/',
    # but contains a '\n/' sequence to test newline sanitization branch
    async def fake_retry2(func, model_type=None):
        await asyncio.sleep(0)
        return "ok\n/inner"

    monkeypatch.setattr(plq, 'retry_with_fallback_models', fake_retry2)

    # create instance without __init__ and set attributes
    inst = object.__new__(PR_LineQuestions)
    inst.git_provider = git
    inst.vars = {}

    # make _load_conversation_history return a sentinel value and ensure it's used
    def load_conv():
        return ['conv message']

    inst._load_conversation_history = load_conv

    async def get_pred_stub(model):
        return "unused"

    inst._get_prediction = get_pred_stub

    # run
    result = await PR_LineQuestions.run(inst)

    assert result == ""
    # conversation_history should have been stored in vars
    assert inst.vars.get('conversation_history') == ['conv message']
    # publish_comment should have been called with sanitized content: "ok\n /inner"
    assert git.published == "ok\n /inner"
