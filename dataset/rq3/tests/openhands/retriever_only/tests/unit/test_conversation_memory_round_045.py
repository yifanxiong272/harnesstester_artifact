import pytest

import openhands.memory.conversation_memory as conv_mod
from openhands.core.message import Message, TextContent, ImageContent


class _SimpleAgentConfig:
    def __init__(self, enable_prompt_extensions=True, disabled_microagents=None):
        self.enable_prompt_extensions = enable_prompt_extensions
        self.disabled_microagents = set(disabled_microagents or [])


class _SimplePromptManager:
    def __init__(self, ws_text="WORKSPACE", micro_text="MICRO"):
        self._ws = ws_text
        self._micro = micro_text

    def build_workspace_context(self, **kwargs):
        return self._ws

    def build_microagent_info(self, **kwargs):
        return self._micro


def _make_memory(monkeypatch, **kwargs):
    cfg = _SimpleAgentConfig(**kwargs.get("agent_config_kwargs", {}))
    pm = _SimplePromptManager(**kwargs.get("prompt_texts", {}))
    # Instantiate ConversationMemory with our simple stubs
    return conv_mod.ConversationMemory(config=cfg, prompt_manager=pm)


def test_mcp_and_ipython_images_round_045(monkeypatch):
    """Covers MCPObservation behavior and IPythonRunCellObservation handling of base64+image URLs.

    - MCPObservation -> should produce a TextContent message with the content passed through/truncated.
    - IPythonRunCellObservation with mixed valid/invalid image URLs and vision_is_active True ->
      should include ImageContent for valid URLs and append a note about filtered images to the text.
    """

    # Prepare module-local fake observation classes and monkeypatch into the module
    class MCPObservation:
        def __init__(self, content):
            self.content = content

    class IPythonRunCellObservation:
        def __init__(self, content, image_urls=None):
            self.content = content
            self.image_urls = image_urls or []

    monkeypatch.setattr(conv_mod, "MCPObservation", MCPObservation)
    monkeypatch.setattr(conv_mod, "IPythonRunCellObservation", IPythonRunCellObservation)

    mem = _make_memory(monkeypatch)

    # Test MCPObservation
    mcp = MCPObservation("mcp-content-123")
    out = mem._process_observation(mcp, tool_call_id_to_message={}, max_message_chars=None)
    assert isinstance(out, list) and len(out) == 1
    msg = out[0]
    assert isinstance(msg, Message)
    assert isinstance(msg.content[0], TextContent)
    assert "mcp-content-123" in msg.content[0].text

    # Test IPythonRunCellObservation with both valid and invalid URLs
    # Make the memory consider one url valid and one invalid
    def fake_is_valid(url):
        return url == "https://valid.example/img.png"

    monkeypatch.setattr(mem, "_is_valid_image_url", fake_is_valid)

    content_with_image = "line1\n![image](data:image/png;base64,AAAA)\nline3"
    ipy = IPythonRunCellObservation(content=content_with_image, image_urls=["https://valid.example/img.png", "bad://url"])

    out2 = mem._process_observation(ipy, tool_call_id_to_message={}, max_message_chars=None, vision_is_active=True)
    assert len(out2) == 1
    imsg = out2[0]
    # Should include both a TextContent and an ImageContent
    types = [type(c) for c in imsg.content]
    assert TextContent in types and ImageContent in types
    # Check that the ImageContent includes only the valid url
    found_image_contents = [c for c in imsg.content if isinstance(c, ImageContent)]
    assert found_image_contents and found_image_contents[0].image_urls == ["https://valid.example/img.png"]
    # The text should include a note about filtered images
    text_parts = [c for c in imsg.content if isinstance(c, TextContent)][0].text
    assert "Note: 1 invalid or empty image(s) were filtered" in text_parts or "filtered from this output" in text_parts


def test_ipython_all_images_invalid_round_045(monkeypatch):
    """Covers the branch where IPythonRunCellObservation has image_urls but none are valid -> text note added.
    """

    class IPythonRunCellObservation:
        def __init__(self, content, image_urls=None):
            self.content = content
            self.image_urls = image_urls or []

    monkeypatch.setattr(conv_mod, "IPythonRunCellObservation", IPythonRunCellObservation)

    mem = _make_memory(monkeypatch)

    # Make all URLs invalid
    monkeypatch.setattr(mem, "_is_valid_image_url", lambda url: False)

    ipy = IPythonRunCellObservation(content="x", image_urls=["bad1", "bad2"]) 
    out = mem._process_observation(ipy, tool_call_id_to_message={}, max_message_chars=None, vision_is_active=True)
    assert len(out) == 1
    msg = out[0]
    # No ImageContent should be present
    assert all(not isinstance(c, ImageContent) for c in msg.content)
    # Check note about all images filtered is present
    assert any(isinstance(c, TextContent) and "All 2 image(s) in this output were invalid or empty" in c.text for c in msg.content)


def test_browser_output_invalid_image_url_round_045(monkeypatch):
    """Covers BrowserOutputObservation branch where image_url exists but is invalid and vision_is_active True.
    This should append a specific note to the text content.
    """

    class BrowserOutputObservation:
        def __init__(self, content, trigger_by_action=None, set_of_marks=None, screenshot=None):
            self.content = content
            self.trigger_by_action = trigger_by_action
            self.set_of_marks = set_of_marks
            self.screenshot = screenshot

    # Patch ActionType enum reference used in the module
    monkeypatch.setattr(conv_mod, "BrowserOutputObservation", BrowserOutputObservation)

    # Create a simple ActionType-like object with BROWSE_INTERACTIVE attribute
    class _AT:
        BROWSE_INTERACTIVE = "BROWSE_INTERACTIVE"

    monkeypatch.setattr(conv_mod, "ActionType", _AT)

    mem = _make_memory(monkeypatch)

    # Force validation to fail for any provided url
    monkeypatch.setattr(mem, "_is_valid_image_url", lambda url: False)

    # Provide a set_of_marks (will choose that before screenshot), and enable SOM visual browsing
    obs = BrowserOutputObservation(content="page text", trigger_by_action=_AT.BROWSE_INTERACTIVE, set_of_marks="bad-set-of-marks")

    out = mem._process_observation(obs, tool_call_id_to_message={}, max_message_chars=None, vision_is_active=True, enable_som_visual_browsing=True)
    assert len(out) == 1
    msg = out[0]
    # There should be only TextContent and it should include a note about the invalid set_of_marks
    assert any(isinstance(c, TextContent) and "set of marks for this webpage was invalid or empty" in c.text for c in msg.content)


def test_loop_detection_returns_empty_round_045(monkeypatch):
    """Covers LoopDetectionObservation early-return branch (returns empty list).
    """

    class LoopDetectionObservation:
        pass

    monkeypatch.setattr(conv_mod, "LoopDetectionObservation", LoopDetectionObservation)

    mem = _make_memory(monkeypatch)

    out = mem._process_observation(LoopDetectionObservation(), tool_call_id_to_message={}, max_message_chars=None)
    assert out == []


def test_recall_workspace_and_microagent_round_045(monkeypatch):
    """Covers RecallObservation WORKSPACE_CONTEXT branch including conversation_instructions and microagent knowledge.
    Ensures that both workspace context and microagent info from the prompt manager are included when present.
    """

    class RecallObservation:
        def __init__(self, recall_type, repo_name=None, repo_directory=None, repo_branch=None, date=None, runtime_hosts=None, additional_agent_instructions=None, custom_secrets_descriptions=None, working_dir=None, conversation_instructions=None, repo_instructions=None, microagent_knowledge=None):
            self.recall_type = recall_type
            self.repo_name = repo_name
            self.repo_directory = repo_directory
            self.repo_branch = repo_branch
            self.date = date
            self.runtime_hosts = runtime_hosts
            self.additional_agent_instructions = additional_agent_instructions
            self.custom_secrets_descriptions = custom_secrets_descriptions
            self.working_dir = working_dir
            self.conversation_instructions = conversation_instructions
            self.repo_instructions = repo_instructions
            self.microagent_knowledge = microagent_knowledge or []

    class MicroagentKnowledge:
        def __init__(self, name, info="info"):
            self.name = name
            self.info = info

    class ConversationInstructions:
        def __init__(self, content):
            self.content = content

    class RecallType:
        WORKSPACE_CONTEXT = "WORKSPACE_CONTEXT"
        KNOWLEDGE = "KNOWLEDGE"

    monkeypatch.setattr(conv_mod, "RecallObservation", RecallObservation)
    monkeypatch.setattr(conv_mod, "MicroagentKnowledge", MicroagentKnowledge)
    monkeypatch.setattr(conv_mod, "ConversationInstructions", ConversationInstructions)
    monkeypatch.setattr(conv_mod, "RecallType", RecallType)

    # Use prompt manager texts to verify they are used
    mem = _make_memory(monkeypatch, prompt_texts={"ws_text": "WSCTX100", "micro_text": "MICROINFO200"}, agent_config_kwargs={"disabled_microagents": []})

    # Provide both repo info and conversation_instructions and microagent knowledge list
    obs = RecallObservation(
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="repo",
        repo_directory=None,
        date="2026-01-01",
        conversation_instructions="do this",
        repo_instructions="some repo instr",
        microagent_knowledge=[MicroagentKnowledge(name="agent1")],
    )

    out = mem._process_observation(obs, tool_call_id_to_message={}, max_message_chars=None)
    assert len(out) == 1
    msg = out[0]
    # Expect workspace and microagent texts from our prompt manager
    texts = [c.text for c in msg.content if isinstance(c, TextContent)]
    assert "WSCTX100" in texts[0]
    assert "MICROINFO200" in texts[-1]


def test_recall_knowledge_filtered_agents_round_045(monkeypatch):
    """Covers RecallObservation KNOWLEDGE branch where filtered agents remain and build_microagent_info is called.
    """

    class RecallObservation:
        def __init__(self, recall_type, microagent_knowledge=None):
            self.recall_type = recall_type
            self.microagent_knowledge = microagent_knowledge or []

    class MicroagentKnowledge:
        def __init__(self, name, info="x"):
            self.name = name
            self.info = info

    # Provide both attributes so attribute access in production code does not raise
    class RecallType:
        KNOWLEDGE = "KNOWLEDGE"
        WORKSPACE_CONTEXT = "WORKSPACE_CONTEXT"

    monkeypatch.setattr(conv_mod, "RecallObservation", RecallObservation)
    monkeypatch.setattr(conv_mod, "MicroagentKnowledge", MicroagentKnowledge)
    monkeypatch.setattr(conv_mod, "RecallType", RecallType)

    mem = _make_memory(monkeypatch, prompt_texts={"micro_text": "BUILD_MICRO"}, agent_config_kwargs={"disabled_microagents": []})

    # Monkeypatch the _filter_agents_in_microagent_obs to return a non-empty list
    monkeypatch.setattr(mem, "_filter_agents_in_microagent_obs", lambda obs, current_index, events: [MicroagentKnowledge("a1")])

    obs = RecallObservation(recall_type=RecallType.KNOWLEDGE, microagent_knowledge=[MicroagentKnowledge("a1")])
    out = mem._process_observation(obs, tool_call_id_to_message={}, max_message_chars=None)
    # Expect a list with a single Message built from build_microagent_info
    assert isinstance(out, list) and len(out) == 1
    assert isinstance(out[0], Message)
    assert any(isinstance(c, TextContent) and "BUILD_MICRO" in c.text for c in out[0].content)
