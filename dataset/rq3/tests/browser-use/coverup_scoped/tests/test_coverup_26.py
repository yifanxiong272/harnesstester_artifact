# file: browser_use/agent/service.py:2896-2985
# asked: {"lines": [2900, 2903, 2904, 2905, 2906, 2907, 2909, 2910, 2911, 2914, 2915, 2917, 2919, 2920, 2921, 2922, 2923, 2927, 2929, 2931, 2932, 2934, 2937, 2939, 2940, 2943, 2944, 2945, 2946, 2947, 2948, 2949, 2950, 2953, 2955, 2956, 2957, 2960, 2961, 2962, 2963, 2966, 2967, 2969, 2970, 2971, 2972, 2973, 2976, 2977, 2978, 2980, 2981, 2982, 2983, 2984], "branches": [[2906, 2907], [2906, 2914], [2929, 2931], [2929, 2934]]}
# gained: {"lines": [2900, 2903, 2904, 2905, 2906, 2907, 2909, 2910, 2911, 2914, 2915, 2917, 2919, 2920, 2921, 2922, 2923, 2927, 2929, 2931, 2932, 2937, 2939, 2940, 2943, 2944, 2945, 2946, 2947, 2948, 2949, 2950, 2953, 2955, 2956, 2957, 2960, 2961, 2962, 2963, 2966, 2967, 2969, 2970, 2971, 2972, 2973, 2976, 2977, 2978, 2980, 2981, 2982, 2983, 2984], "branches": [[2906, 2907], [2906, 2914], [2929, 2931]]}

import logging
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_generate_rerun_summary_structured_success(monkeypatch):
    from browser_use.agent.service import Agent
    from browser_use.agent.views import RerunSummaryAction

    # Patch prompt builders
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_rerun_summary_prompt",
        lambda original_task, total_steps, success_count, error_count: "DUMMY PROMPT",
    )

    captured_message = {}

    def fake_get_message(prompt, screenshot_b64):
        captured_message["prompt"] = prompt
        captured_message["screenshot_b64"] = screenshot_b64
        # Return an object that can act as a BaseMessage (simple namespace is fine)
        return SimpleNamespace(content=prompt)

    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", fake_get_message)

    # Dummy browser session that returns bytes for screenshot
    class DummyBrowserSession:
        async def take_screenshot(self, full_page=False):
            return b"\x00\x01"

    # Dummy LLM that supports structured output
    class DummyLLM:
        model = "dummy-model/1.0"

        async def ainvoke(self, messages, *args, **kwargs):
            # Expect structured output via kwargs['output_format']
            if kwargs.get("output_format") is RerunSummaryAction:
                return SimpleNamespace(completion=RerunSummaryAction(summary="All good", success=True, completion_status="complete"))
            return SimpleNamespace(completion="fallback")

    # Minimal agent that avoids heavy Agent.__init__
    class DummyAgent(Agent):
        def __init__(self):
            # Do not call super().__init__
            self.browser_session = DummyBrowserSession()
            self.llm = DummyLLM()
            self._logger = logging.getLogger("test_agent_structured_success")

        @property
        def logger(self):
            return self._logger

    agent = DummyAgent()

    # Build results: two steps, none have error
    results = [SimpleNamespace(error=False), SimpleNamespace(error=False)]

    result = await agent._generate_rerun_summary("original task", results)

    assert result.is_done is True
    assert result.success is True
    assert "All good" in result.extracted_content
    assert "complete" in result.long_term_memory

    # Ensure message builder received base64-encoded screenshot (non-empty)
    assert captured_message["screenshot_b64"] is not None
    assert isinstance(captured_message["screenshot_b64"], str)
    assert captured_message["prompt"] == "DUMMY PROMPT"


@pytest.mark.asyncio
async def test_generate_rerun_summary_structured_fallback_to_text(monkeypatch):
    from browser_use.agent.service import Agent

    # Monkeypatch prompts
    monkeypatch.setattr(
        "browser_use.agent.prompts.get_rerun_summary_prompt",
        lambda original_task, total_steps, success_count, error_count: "PROMPT2",
    )
    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", lambda prompt, screenshot_b64: SimpleNamespace(content=prompt))

    # Dummy browser session returns no screenshot (None)
    class DummyBrowserSession:
        async def take_screenshot(self, full_page=False):
            return None

    # Dummy LLM that fails structured output then returns text
    class DummyLLM:
        model = "dummy-model/2.0"

        async def ainvoke(self, messages, *args, **kwargs):
            # If structured requested via kwargs -> raise to trigger fallback
            if kwargs.get("output_format") is not None:
                raise RuntimeError("structured not supported")
            # The code calls ainvoke(messages, None) for fallback; return a simple text completion
            return SimpleNamespace(completion="Textual summary of rerun")

    class DummyAgent(Agent):
        def __init__(self):
            self.browser_session = DummyBrowserSession()
            self.llm = DummyLLM()
            self._logger = logging.getLogger("test_agent_structured_fallback")

        @property
        def logger(self):
            return self._logger

    agent = DummyAgent()

    # Build results: two steps, one with error to produce failure
    results = [SimpleNamespace(error=True), SimpleNamespace(error=False)]

    result = await agent._generate_rerun_summary("orig task", results)

    # Because there was an error, success should be False
    assert result.is_done is True
    assert result.success is False
    # extracted content should be the text returned by LLM fallback
    assert result.extracted_content == "Textual summary of rerun"
    # long_term_memory should contain the rerun status phrase created from the summary
    assert "Rerun completed with status" in result.long_term_memory


@pytest.mark.asyncio
async def test_generate_rerun_summary_outer_exception_fallback(monkeypatch):
    from browser_use.agent.service import Agent

    # Force get_rerun_summary_message to raise to trigger the outer exception handler
    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_prompt", lambda original_task, total_steps, success_count, error_count: "PROMPT3")

    def raising_message(prompt, screenshot_b64):
        raise ValueError("message builder failed")

    monkeypatch.setattr("browser_use.agent.prompts.get_rerun_summary_message", raising_message)

    # Browser session that raises on screenshot to exercise screenshot exception path
    class FailingBrowserSession:
        async def take_screenshot(self, full_page=False):
            raise RuntimeError("screenshot failure")

    class DummyLLM:
        model = "dummy-model/3.0"

        async def ainvoke(self, messages, *args, **kwargs):
            return SimpleNamespace(completion="should not be used")

    class DummyAgent(Agent):
        def __init__(self):
            self.browser_session = FailingBrowserSession()
            self.llm = DummyLLM()
            self._logger = logging.getLogger("test_agent_outer_exception")

        @property
        def logger(self):
            return self._logger

    agent = DummyAgent()

    # Results: mix of successes and failures
    results = [SimpleNamespace(error=False), SimpleNamespace(error=True), SimpleNamespace(error=False)]

    result = await agent._generate_rerun_summary("original", results)

    # Should return fallback ActionResult created in the outer except block
    assert result.is_done is True
    # success is determined by error_count == 0 (there is one error -> False)
    assert result.success is False
    # extracted_content should include 'Rerun completed' and the succeeded count "2/3"
    assert "Rerun completed" in result.extracted_content
    assert "2/3" in result.extracted_content
    # long_term_memory indicates counts
    assert "2 steps succeeded" in result.long_term_memory
    assert "1 errors" in result.long_term_memory
