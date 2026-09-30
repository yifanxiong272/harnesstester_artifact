import asyncio
import pytest

# The tests patch many symbols that Agent._execute_ai_step imports at runtime.
# They construct a minimal 'self' object with the attributes the method expects
# (llm, logger, browser_session, file_system) to avoid instantiating the full Agent.

class SimpleActionResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeLogger:
    def __init__(self):
        self.debug_messages = []
        self.info_messages = []
        self.warn_messages = []

    def debug(self, msg, *args, **kwargs):
        self.debug_messages.append(msg)

    def info(self, msg, *args, **kwargs):
        self.info_messages.append(msg)

    def warning(self, msg, *args, **kwargs):
        self.warn_messages.append(msg)


class FakeLLMSmall:
    def __init__(self):
        self.model = "fake-small"

    class Response:
        def __init__(self, completion):
            self.completion = completion

    async def ainvoke(self, messages):
        # Return a small completion so extracted_content stays under MAX_MEMORY_LENGTH
        return FakeLLMSmall.Response(completion="short result")


class FakeLLMLarge:
    def __init__(self):
        self.model = "fake-large"

    class Response:
        def __init__(self, completion):
            self.completion = completion

    async def ainvoke(self, messages):
        # Return a large completion to push extracted_content length over the MAX_MEMORY_LENGTH
        return FakeLLMLarge.Response(completion=("X" * 2000))


class FakeBrowserSession:
    def __init__(self, screenshot_bytes=None, screenshot_raises=False, current_url="https://example.test"):
        self._screenshot = screenshot_bytes
        self._screenshot_raises = screenshot_raises
        self._current_url = current_url

    async def take_screenshot(self, full_page=False):
        if self._screenshot_raises:
            raise RuntimeError("screenshot failed")
        return self._screenshot

    async def get_current_page_url(self):
        return self._current_url


class FakeFileSystem:
    def __init__(self):
        self.saved = []

    async def save_extracted_content(self, content):
        name = "saved_file.txt"
        self.saved.append((name, content))
        return name


# Utilities used to replace imported callables / classes inside the function
async def _noop_extract(browser_session, extract_links=False):
    # default extractor returns sample content and stats
    content = "# Title\nSome content"
    stats = {
        "original_html_chars": 100,
        "initial_markdown_chars": 80,
        "final_filtered_chars": 80,
        "filtered_chars_removed": 0,
    }
    return content, stats


@pytest.mark.asyncio
async def test_execute_ai_step_small_memory_round_043(monkeypatch):
    """Successful flow: small completion, no screenshot, no filtered chars.

    Asserts: extracted_content is constructed, include_extracted_content_only_once is False,
    and long_term_memory equals the extracted_content.
    """
    # Patch the runtime imports the function performs
    monkeypatch.setattr("browser_use.agent.service.ActionResult", SimpleActionResult)
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYS_PROMPT")
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_ai_step_user_prompt",
        lambda query, stats, content: f"PROMPT:{query}|{stats[:20]}",
    )
    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", lambda prompt, screenshot_b64: None)
    # Replace message classes with simple containers
    class SysMsg:
        def __init__(self, content):
            self.content = content

    class UserMsg:
        def __init__(self, content=None):
            self.content = content

    monkeypatch.setattr("browser_use.llm.messages.SystemMessage", SysMsg)
    monkeypatch.setattr("browser_use.llm.messages.UserMessage", UserMsg)
    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda x: x)
    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", _noop_extract)

    # Prepare fake components
    fake_llm = FakeLLMSmall()
    fake_logger = FakeLogger()
    fake_browser = FakeBrowserSession(screenshot_bytes=None, current_url="https://a.test/page")
    fake_fs = FakeFileSystem()

    # Build minimal self object
    class DummySelf:
        pass

    self = DummySelf()
    self.llm = fake_llm
    self.logger = fake_logger
    self.browser_session = fake_browser
    self.file_system = fake_fs

    # Import the method and run it
    from browser_use.agent.service import Agent

    result = await Agent._execute_ai_step(self, query="inspect", include_screenshot=False, extract_links=False, ai_step_llm=None)

    # Assertions about ActionResult fields
    assert hasattr(result, "extracted_content")
    assert "<url>" in result.extracted_content
    assert "<query>" in result.extracted_content
    assert "short result" in result.extracted_content
    assert result.include_extracted_content_only_once is False
    assert result.long_term_memory == result.extracted_content


@pytest.mark.asyncio
async def test_execute_ai_step_large_memory_and_screenshot_round_043(monkeypatch):
    """Flow: screenshot present and large response triggers save_extracted_content branch and get_rerun_summary_message usage.

    Asserts: file_system.save_extracted_content called, include_extracted_content_only_once True,
    and the rerun summary prompt function is used when screenshot is provided.
    """
    # Patch ActionResult and sanitize
    monkeypatch.setattr("browser_use.agent.service.ActionResult", SimpleActionResult)
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYS_PROMPT")

    # Prepare a sentinel to verify get_ai_step_user_prompt got the expected inputs
    captured = {}

    def fake_get_user_prompt(query, stats_summary, content):
        captured['query'] = query
        captured['stats'] = stats_summary
        captured['content'] = content
        return f"PROMPT:{query}|{stats_summary}"

    def fake_get_rerun_summary_message(prompt_text, screenshot_b64):
        # Return an object compatible with the LLM call (has content attribute when wrapped as a user message)
        class RS:
            def __init__(self, content):
                self.content = content

        captured['screenshot_b64'] = screenshot_b64
        return RS(content=prompt_text + "|WITH_SCREENSHOT")

    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_user_prompt", fake_get_user_prompt)
    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", fake_get_rerun_summary_message)

    # Replace message classes (SystemMessage used by the LLM invocation)
    class SysMsg:
        def __init__(self, content):
            self.content = content

    monkeypatch.setattr("browser_use.llm.messages.SystemMessage", SysMsg)

    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda x: x)

    # Make extractor return some filtered chars > 0 to exercise stats_summary addition
    async def extractor_with_filtered(browser_session, extract_links=False):
        content = "# Big Content\nLots of stuff"
        stats = {
            "original_html_chars": 5000,
            "initial_markdown_chars": 4000,
            "final_filtered_chars": 3000,
            "filtered_chars_removed": 1000,
        }
        return content, stats

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", extractor_with_filtered)

    # Prepare large LLM and browser session which returns screenshot bytes
    fake_llm = FakeLLMLarge()
    fake_logger = FakeLogger()
    fake_browser = FakeBrowserSession(screenshot_bytes=b"abc", current_url="https://big.test/page")
    fake_fs = FakeFileSystem()

    class DummySelf:
        pass

    self = DummySelf()
    self.llm = fake_llm
    self.logger = fake_logger
    self.browser_session = fake_browser
    self.file_system = fake_fs

    from browser_use.agent.service import Agent

    result = await Agent._execute_ai_step(self, query="analyze", include_screenshot=True, extract_links=True, ai_step_llm=None)

    # Because the completion is very large, file_system.save_extracted_content should have been called
    assert fake_fs.saved, "Expected save_extracted_content to be called for large extracted content"
    assert result.include_extracted_content_only_once is True
    assert "Content in saved_file.txt" in result.long_term_memory

    # The rerun summary message should have been built with a base64 screenshot; b64 of b'abc' is 'YWJj'
    assert captured.get('screenshot_b64') == "YWJj"
    # The prompt text was populated and forwarded
    assert captured.get('query') == "analyze"
    assert "filtered 1,000" in captured.get('stats') or "filtered 1000" in captured.get('stats')


@pytest.mark.asyncio
async def test_execute_ai_step_extract_failure_round_043(monkeypatch):
    """If extract_clean_markdown raises, the function should return an ActionResult with an error string mentioning the exception type and message."""
    monkeypatch.setattr("browser_use.agent.service.ActionResult", SimpleActionResult)

    async def raising_extractor(browser_session, extract_links=False):
        raise ValueError("boom")

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", raising_extractor)

    class DummySelf:
        pass

    self = DummySelf()
    self.llm = FakeLLMSmall()
    self.logger = FakeLogger()
    self.browser_session = FakeBrowserSession()
    self.file_system = FakeFileSystem()

    from browser_use.agent.service import Agent

    result = await Agent._execute_ai_step(self, query="q", include_screenshot=False, extract_links=False, ai_step_llm=None)
    assert hasattr(result, "error")
    assert "Could not extract clean markdown" in result.error
    assert "ValueError" in result.error


@pytest.mark.asyncio
async def test_execute_ai_step_llm_failure_round_043(monkeypatch):
    """If the LLM invocation raises, the function should return an ActionResult with an error string starting with 'AI step failed'."""
    monkeypatch.setattr("browser_use.agent.service.ActionResult", SimpleActionResult)
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_system_prompt", lambda: "SYS_PROMPT")
    monkeypatch.setattr("browser_use.agent.prompts.get_ai_step_user_prompt", lambda q, s, c: "PROMPT")
    monkeypatch.setattr("browser_use.llm.messages.SystemMessage", lambda content: type("M", (), {"content": content}))
    monkeypatch.setattr("browser_use.llm.messages.UserMessage", lambda content=None: type("M", (), {"content": content}))
    monkeypatch.setattr("browser_use.utils.sanitize_surrogates", lambda x: x)

    async def extractor_ok(browser_session, extract_links=False):
        return "content", {
            "original_html_chars": 10,
            "initial_markdown_chars": 9,
            "final_filtered_chars": 9,
            "filtered_chars_removed": 0,
        }

    monkeypatch.setattr("browser_use.dom.markdown_extractor.extract_clean_markdown", extractor_ok)

    class FailingLLM:
        def __init__(self):
            self.model = "fail"

        async def ainvoke(self, messages):
            raise RuntimeError("llm died")

    class DummySelf:
        pass

    self = DummySelf()
    self.llm = FailingLLM()
    self.logger = FakeLogger()
    self.browser_session = FakeBrowserSession()
    self.file_system = FakeFileSystem()

    from browser_use.agent.service import Agent

    result = await Agent._execute_ai_step(self, query="q", include_screenshot=False, extract_links=False, ai_step_llm=None)
    assert hasattr(result, "error")
    assert result.error.startswith("AI step failed"), result.error
