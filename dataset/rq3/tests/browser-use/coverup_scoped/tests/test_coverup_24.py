# file: browser_use/agent/service.py:2987-3090
# asked: {"lines": [3007, 3008, 3009, 3012, 3013, 3016, 3017, 3019, 3020, 3022, 3023, 3026, 3027, 3028, 3029, 3030, 3031, 3033, 3034, 3035, 3038, 3039, 3040, 3041, 3043, 3044, 3045, 3048, 3049, 3052, 3053, 3056, 3057, 3059, 3061, 3062, 3064, 3066, 3067, 3068, 3072, 3073, 3074, 3075, 3077, 3078, 3079, 3081, 3082, 3083, 3084, 3085, 3087, 3088, 3089, 3090], "branches": [[3027, 3028], [3027, 3038], [3030, 3031], [3030, 3038], [3044, 3045], [3044, 3048], [3056, 3057], [3056, 3059], [3073, 3074], [3073, 3077]]}
# gained: {"lines": [3007, 3008, 3009, 3012, 3013, 3016, 3017, 3019, 3020, 3022, 3023, 3026, 3027, 3028, 3029, 3030, 3031, 3033, 3038, 3039, 3040, 3041, 3043, 3044, 3045, 3048, 3049, 3052, 3053, 3056, 3057, 3059, 3061, 3062, 3064, 3066, 3067, 3068, 3072, 3073, 3074, 3075, 3077, 3078, 3079, 3081, 3082, 3083, 3084, 3085, 3087, 3088, 3089, 3090], "branches": [[3027, 3028], [3027, 3038], [3030, 3031], [3044, 3045], [3044, 3048], [3056, 3057], [3056, 3059], [3073, 3074], [3073, 3077]]}

import asyncio
import types
import pytest

from types import SimpleNamespace

from browser_use.agent.service import Agent
from browser_use.llm.messages import UserMessage
from browser_use.agent.views import ActionResult


class DummyLogger:
    def __init__(self):
        self.records = {"debug": [], "info": [], "warning": []}

    def debug(self, *args, **kwargs):
        self.records["debug"].append((args, kwargs))

    def info(self, *args, **kwargs):
        self.records["info"].append((args, kwargs))

    def warning(self, *args, **kwargs):
        self.records["warning"].append((args, kwargs))


class DummyBrowserSession:
    def __init__(self, screenshot_bytes=None, url="http://example.com"):
        self._screenshot = screenshot_bytes
        self._url = url
        self.take_screenshot_calls = 0
        self.get_current_page_url_calls = 0

    async def take_screenshot(self, full_page=False):
        self.take_screenshot_calls += 1
        return self._screenshot

    async def get_current_page_url(self):
        self.get_current_page_url_calls += 1
        return self._url


class DummyFileSystem:
    def __init__(self, saved_name="saved_file.txt"):
        self.saved = []
        self.saved_name = saved_name

    async def save_extracted_content(self, content):
        self.saved.append(content)
        return self.saved_name


class DummyLLM:
    def __init__(self, model="dummy-model", completion="ok", raise_on_invoke=None):
        self.model = model
        self._completion = completion
        self.raise_on_invoke = raise_on_invoke
        self.invoked_with = None

    async def ainvoke(self, messages):
        self.invoked_with = messages
        if self.raise_on_invoke:
            raise self.raise_on_invoke
        return SimpleNamespace(completion=self._completion)


@pytest.mark.asyncio
async def test_execute_ai_step_success_no_screenshot_small_memory(monkeypatch):
    # Arrange: patch markdown extractor and prompts & sanitize
    async def fake_extract_clean_markdown(browser_session, extract_links=False):
        content = "clean markdown content"
        stats = {
            "original_html_chars": 1_000,
            "initial_markdown_chars": 800,
            "final_filtered_chars": 500,
            "filtered_chars_removed": 0,
        }
        return content, stats

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", fake_extract_clean_markdown)

    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYSTEM_PROMPT")
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_ai_step_user_prompt",
        lambda query, stats_summary, content: f"PROMPT: {query} | {stats_summary} | {content}",
    )
    # No screenshot path, so this won't be used but define anyway
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_rerun_summary_message",
        lambda prompt_text, screenshot_b64: UserMessage(content=prompt_text + "::" + screenshot_b64),
    )

    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda s: s)

    # Dummy environment
    browser_session = DummyBrowserSession(screenshot_bytes=None, url="http://no-screenshot.example")
    file_system = DummyFileSystem()
    llm = DummyLLM(completion="LLM_RESULT_SMALL")
    logger = DummyLogger()

    dummy_self = SimpleNamespace(
        llm=llm,
        browser_session=browser_session,
        file_system=file_system,
        logger=logger,
    )

    # Act
    result: ActionResult = await Agent._execute_ai_step(dummy_self, query="Find me", include_screenshot=False, extract_links=False, ai_step_llm=None)

    # Assert
    assert result.error is None
    assert result.extracted_content is not None
    assert "http://no-screenshot.example" in result.extracted_content
    assert "<query>\nFind me\n</query>" in result.extracted_content
    assert "LLM_RESULT_SMALL" in result.extracted_content
    assert result.include_extracted_content_only_once is False
    assert result.long_term_memory == result.extracted_content
    # Ensure file_system not used
    assert file_system.saved == []


@pytest.mark.asyncio
async def test_execute_ai_step_with_screenshot_large_memory(monkeypatch):
    # Arrange: markdown extractor returns filtered chars > 0 to exercise stats summary branch
    async def fake_extract_clean_markdown(browser_session, extract_links=False):
        content = "clean markdown content with links"
        stats = {
            "original_html_chars": 10_000,
            "initial_markdown_chars": 8_000,
            "final_filtered_chars": 6_000,
            "filtered_chars_removed": 2_000,
        }
        return content, stats

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", fake_extract_clean_markdown)

    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYSTEM_PROMPT")
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_ai_step_user_prompt",
        lambda query, stats_summary, content: f"PROMPT: {query} | {stats_summary} | {content}",
    )
    # For screenshot branch, return a UserMessage object
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_rerun_summary_message",
        lambda prompt_text, screenshot_b64: UserMessage(content=prompt_text + "::" + screenshot_b64),
    )

    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda s: s)

    # Prepare a screenshot and a very large LLM completion to force file save branch
    screenshot_bytes = b"\x89PNG\r\n" + b"x" * 100
    browser_session = DummyBrowserSession(screenshot_bytes=screenshot_bytes, url="http://screenshot.example")
    file_system = DummyFileSystem(saved_name="big_file.txt")
    # create a large completion to exceed MAX_MEMORY_LENGTH when combined into extracted_content
    large_completion = "X" * 2000
    llm = DummyLLM(completion=large_completion)
    logger = DummyLogger()

    dummy_self = SimpleNamespace(
        llm=llm,
        browser_session=browser_session,
        file_system=file_system,
        logger=logger,
    )

    # Act
    result: ActionResult = await Agent._execute_ai_step(dummy_self, query="Large Content Query", include_screenshot=True, extract_links=True, ai_step_llm=None)

    # Assert
    assert result.error is None
    assert result.include_extracted_content_only_once is True
    assert "big_file.txt" in result.long_term_memory
    # file system save should have been called with the large extracted content
    assert len(file_system.saved) == 1
    assert "Large Content Query" in file_system.saved[0]
    # The extracted_content should still include the URL and query (even though memory saved to file)
    assert "<url>\nhttp://screenshot.example\n</url>" in result.extracted_content
    assert "<query>\nLarge Content Query\n</query>" in result.extracted_content


@pytest.mark.asyncio
async def test_execute_ai_step_extract_markdown_failure_returns_error(monkeypatch):
    # Arrange: make extractor raise
    async def raising_extract(browser_session, extract_links=False):
        raise RuntimeError("extraction failed")

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", raising_extract)
    # Simplest other patches
    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda s: s)
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYSTEM")
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_user_prompt", lambda q, s, c: "PROMPT")
    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", lambda p, s: UserMessage(content=p))

    browser_session = DummyBrowserSession()
    file_system = DummyFileSystem()
    llm = DummyLLM()
    logger = DummyLogger()
    dummy_self = SimpleNamespace(
        llm=llm,
        browser_session=browser_session,
        file_system=file_system,
        logger=logger,
    )

    # Act
    result: ActionResult = await Agent._execute_ai_step(dummy_self, query="Q", include_screenshot=False, extract_links=False, ai_step_llm=None)

    # Assert: should return error mentioning the extractor exception
    assert result.error is not None
    assert "Could not extract clean markdown: RuntimeError" in result.error


@pytest.mark.asyncio
async def test_execute_ai_step_llm_failure_returns_error(monkeypatch):
    # Arrange: normal extraction but llm fails
    async def fake_extract_clean_markdown(browser_session, extract_links=False):
        return "content", {
            "original_html_chars": 100,
            "initial_markdown_chars": 80,
            "final_filtered_chars": 50,
            "filtered_chars_removed": 0,
        }

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", fake_extract_clean_markdown)
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYSTEM_PROMPT")
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_user_prompt", lambda q, s, c: "PROMPT")
    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", lambda p, s: UserMessage(content=p))
    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda s: s)

    browser_session = DummyBrowserSession()
    file_system = DummyFileSystem()
    # llm that raises on ainvoke
    llm = DummyLLM(raise_on_invoke=ValueError("llm failed"))
    logger = DummyLogger()
    dummy_self = SimpleNamespace(
        llm=llm,
        browser_session=browser_session,
        file_system=file_system,
        logger=logger,
    )

    # Act
    result: ActionResult = await Agent._execute_ai_step(dummy_self, query="Q", include_screenshot=False, extract_links=False, ai_step_llm=None)

    # Assert
    assert result.error is not None
    assert "AI step failed" in result.error
    assert "llm failed" in result.error
