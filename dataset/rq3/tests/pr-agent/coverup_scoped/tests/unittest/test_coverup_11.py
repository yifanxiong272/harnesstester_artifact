# file: pr_agent/tools/pr_help_docs.py:329-394
# asked: {"lines": [330, 331, 332, 334, 336, 339, 340, 341, 342, 343, 350, 351, 352, 353, 355, 356, 358, 359, 360, 362, 364, 365, 366, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 384, 385, 386, 388, 389, 391, 392, 393, 394], "branches": [[330, 331], [330, 334], [340, 341], [340, 343], [353, 355], [353, 358], [358, 359], [358, 362], [369, 370], [369, 372], [374, 375], [374, 378], [378, 379], [378, 384], [385, 386], [385, 388], [388, 389], [388, 391]]}
# gained: {"lines": [330, 331, 332, 334, 336, 339, 340, 341, 342, 343, 350, 351, 352, 353, 355, 356, 358, 359, 360, 362, 364, 365, 366, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 384, 385, 386, 388, 389, 392, 393, 394], "branches": [[330, 331], [330, 334], [340, 341], [340, 343], [353, 355], [353, 358], [358, 359], [358, 362], [369, 370], [369, 372], [374, 375], [374, 378], [378, 379], [378, 384], [385, 386], [385, 388], [388, 389]]}

import types
import pytest

import pr_agent.tools.pr_help_docs as phd_mod
from pr_agent.tools.pr_help_docs import PRHelpDocs


class DummySettings:
    def __init__(self, publish_output=True):
        self.pr_help_docs_prompts = types.SimpleNamespace(system="sys", user="usr")
        self.config = types.SimpleNamespace(publish_output=publish_output)
        self._dict = {
            'PR_HELP_DOCS.REPO_URL': '',
            'PR_HELP_DOCS.REPO_DEFAULT_BRANCH': 'main',
            'PR_HELP_DOCS.EXCLUDE_ROOT_README': False,
            'PR_HELP_DOCS.SUPPORTED_DOC_EXTS': ['.md'],
            'PR_HELP_DOCS.DOCS_PATH': 'docs'
        }

    def get(self, k, default=None):
        return self._dict.get(k, default)

    def __getitem__(self, k):
        return self._dict[k]


class DummyGitProvider:
    def __init__(self):
        self.published = []

    def get_git_repo_url(self, ctx):
        return "https://example.com/repo.git"

    def publish_comment(self, text):
        self.published.append(text)


class FullDummyLogger:
    def __init__(self, record=None):
        self.record = record or {}

    def debug(self, *a, **k):
        self.record.setdefault("debug", []).append((a, k))

    def warning(self, *a, **k):
        self.record.setdefault("warning", []).append((a, k))

    def error(self, *a, **k):
        self.record.setdefault("error", []).append((a, k))

    def exception(self, *a, **k):
        self.record.setdefault("exception", []).append((a, k))

    def info(self, *a, **k):
        self.record.setdefault("info", []).append((a, k))


def make_env(monkeypatch, publish_output=True):
    # Patch settings and git provider and TokenHandler and logger
    monkeypatch.setattr(phd_mod, "get_settings", lambda: DummySettings(publish_output=publish_output))
    monkeypatch.setattr(phd_mod, "get_git_provider_with_context", lambda ctx: DummyGitProvider())
    monkeypatch.setattr(phd_mod, "TokenHandler", lambda *a, **k: types.SimpleNamespace())
    # Provide a full logger by default
    monkeypatch.setattr(phd_mod, "get_logger", lambda: FullDummyLogger())


@pytest.mark.asyncio
async def test_run_no_question(monkeypatch):
    make_env(monkeypatch)
    # Create instance with no args -> question None
    inst = PRHelpDocs("dummy_ctx", ai_handler=lambda: types.SimpleNamespace(), args=None)
    assert inst.question is None
    res = await inst.run()
    assert res is None


@pytest.mark.asyncio
async def test_run_no_docs_found(monkeypatch):
    make_env(monkeypatch)
    # create instance with a question
    inst = PRHelpDocs("ctx", ai_handler=lambda: types.SimpleNamespace(), args=("some question",))
    inst.question = "some question"
    monkeypatch.setattr(inst, "_gen_filenames_to_contents_map_from_repo", lambda: {})
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "")
    # run should return None when no docs
    res = await inst.run()
    assert res is None


@pytest.mark.asyncio
async def test_run_trim_and_rank_returns_empty(monkeypatch):
    make_env(monkeypatch)
    inst = PRHelpDocs("ctx", ai_handler=lambda: types.SimpleNamespace(), args=("q",))
    inst.question = "q"
    monkeypatch.setattr(inst, "_gen_filenames_to_contents_map_from_repo", lambda: {"file.md": "content"})
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "full content")
    monkeypatch.setattr(phd_mod, "get_maximal_text_input_length_for_token_count_estimation", lambda: 10)
    monkeypatch.setattr(inst, "_trim_docs_input", lambda docs, maxlen, only_return_if_trim_needed=False: True)

    async def fake_rank(docs, max_allowed):
        return ""
    monkeypatch.setattr(inst, "_rank_docs_and_return_them_as_prompt", fake_rank)
    # Ensure logger exists with error method (make_env provided one)
    res = await inst.run()
    assert res is None


@pytest.mark.asyncio
async def test_run_load_yaml_fails(monkeypatch):
    make_env(monkeypatch)
    inst = PRHelpDocs("ctx", ai_handler=lambda: types.SimpleNamespace(), args=("q",))
    inst.question = "q"
    monkeypatch.setattr(inst, "_gen_filenames_to_contents_map_from_repo", lambda: {"a": "b"})
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "prompt")
    monkeypatch.setattr(inst, "_trim_docs_input", lambda docs, maxlen, only_return_if_trim_needed=False: False)
    monkeypatch.setattr(phd_mod, "get_maximal_text_input_length_for_token_count_estimation", lambda: 10000)

    async def fake_retry(prep, model_type=None):
        return "raw response"
    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)

    monkeypatch.setattr(phd_mod, "load_yaml", lambda r: None)
    # get_logger already provides exception in make_env
    res = await inst.run()
    assert res is None


@pytest.mark.asyncio
async def test_run_missing_response_parts_and_not_relevant(monkeypatch):
    make_env(monkeypatch)
    inst = PRHelpDocs("ctx", ai_handler=lambda: types.SimpleNamespace(), args=("q",))
    inst.question = "q"
    monkeypatch.setattr(inst, "_gen_filenames_to_contents_map_from_repo", lambda: {"a": "b"})
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "prompt")
    monkeypatch.setattr(inst, "_trim_docs_input", lambda docs, maxlen, only_return_if_trim_needed=False: False)
    monkeypatch.setattr(phd_mod, "get_maximal_text_input_length_for_token_count_estimation", lambda: 10000)

    async def fake_retry(prep, model_type=None):
        return "raw response"
    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)

    # Case 1: missing response_str or relevant_sections
    monkeypatch.setattr(phd_mod, "load_yaml", lambda r: {"response": None, "relevant_sections": None})
    res1 = await inst.run()
    assert res1 is None

    # Case 2: question_is_relevant == '0'
    monkeypatch.setattr(phd_mod, "load_yaml", lambda r: {"response": "r", "relevant_sections": [{"a": "b"}], "question_is_relevant": "0"})
    res2 = await inst.run()
    assert res2 is None


@pytest.mark.asyncio
async def test_run_return_as_string_and_publish_branches(monkeypatch):
    # Test both return_as_string True (no publish) and False (publish)
    make_env(monkeypatch, publish_output=True)
    inst = PRHelpDocs("ctx", ai_handler=lambda: types.SimpleNamespace(), args=("q",))
    inst.question = "q"

    monkeypatch.setattr(inst, "_gen_filenames_to_contents_map_from_repo", lambda: {"file.md": "content"})
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "full content")
    monkeypatch.setattr(inst, "_trim_docs_input", lambda docs, maxlen, only_return_if_trim_needed=False: False)
    monkeypatch.setattr(phd_mod, "get_maximal_text_input_length_for_token_count_estimation", lambda: 10000)

    async def fake_retry(prep, model_type=None):
        return "raw response"
    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)

    monkeypatch.setattr(phd_mod, "load_yaml", lambda r: {"response": "the answer", "relevant_sections": [{"title": "t", "snippet": "s"}], "question_is_relevant": "1"})
    monkeypatch.setattr(inst, "_format_model_answer", lambda response_str, relevant_sections: "FORMATTED ANSWER")

    # Replace git_provider with dummy that records publish_comment
    inst.git_provider = DummyGitProvider()

    # Case A: return_as_string True -> should return answer string and not publish
    inst.return_as_string = True
    res = await inst.run()
    assert res == "FORMATTED ANSWER"
    assert inst.git_provider.published == []

    # Case B: return_as_string False and publish_output True -> should publish and return answer
    inst.return_as_string = False
    res2 = await inst.run()
    assert res2 == "FORMATTED ANSWER"
    assert inst.git_provider.published == ["FORMATTED ANSWER"]


@pytest.mark.asyncio
async def test_run_exception_in_processing_logs_and_returns_none(monkeypatch):
    make_env(monkeypatch)
    inst = PRHelpDocs("ctx", ai_handler=lambda: types.SimpleNamespace(), args=("q",))
    inst.question = "q"
    monkeypatch.setattr(inst, "_gen_filenames_to_contents_map_from_repo", lambda: {"file.md": "content"})
    monkeypatch.setattr(phd_mod, "aggregate_documentation_files_for_prompt_contents", lambda d: "full content")
    monkeypatch.setattr(inst, "_trim_docs_input", lambda docs, maxlen, only_return_if_trim_needed=False: False)
    monkeypatch.setattr(phd_mod, "get_maximal_text_input_length_for_token_count_estimation", lambda: 10000)

    async def fake_retry(prep, model_type=None):
        return "raw response"
    monkeypatch.setattr(phd_mod, "retry_with_fallback_models", fake_retry)

    monkeypatch.setattr(phd_mod, "load_yaml", lambda r: {"response": "r", "relevant_sections": [{"t": "s"}], "question_is_relevant": "1"})

    def raise_exc(response_str, relevant_sections):
        raise RuntimeError("boom")
    monkeypatch.setattr(inst, "_format_model_answer", raise_exc)

    # capture exception calls
    called = {"ex": False}
    def fake_get_logger():
        return FullDummyLogger(record={"exception_called": called})
    monkeypatch.setattr(phd_mod, "get_logger", lambda: FullDummyLogger())

    res = await inst.run()
    assert res is None
