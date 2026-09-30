import importlib
from types import SimpleNamespace

import pytest

# Load the module under test
cm = importlib.import_module("openhands.memory.conversation_memory")

# Helper: replace several symbols in the module with simple deterministic fakes
def _patch_basic_symbols(
    *,
    truncate_identity=True,
    textcontent_cls=None,
    imagecontent_cls=None,
    message_cls=None,
    mcp_cls=None,
    ipy_cls=None,
    browser_cls=None,
    recall_cls=None,
    microagent_cls=None,
    recall_type=None,
):
    # truncate_content -> identity (deterministic)
    if truncate_identity:
        cm.truncate_content = lambda s, max_chars=None: s

    # Simple TextContent / ImageContent / Message fakes
    class TextContentFake:
        def __init__(self, text: str = ""):
            self.text = text

        def __repr__(self):
            return f"TextContent(text={self.text!r})"

    class ImageContentFake:
        def __init__(self, image_urls):
            self.image_urls = list(image_urls) if image_urls is not None else []

        def __repr__(self):
            return f"ImageContent(image_urls={self.image_urls!r})"

    class MessageFake:
        def __init__(self, role: str, content=None, tool_call_id=None, name=None):
            self.role = role
            self.content = content or []
            self.tool_call_id = tool_call_id
            self.name = name

        def __repr__(self):
            return f"Message(role={self.role!r}, content={self.content!r})"

    cm.TextContent = textcontent_cls or TextContentFake
    cm.ImageContent = imagecontent_cls or ImageContentFake
    cm.Message = message_cls or MessageFake

    # Observation fakes
    class MCPFake:
        def __init__(self, content: str):
            self.content = content

    class IPyFake:
        def __init__(self, content: str, image_urls=None):
            self.content = content
            self.image_urls = image_urls or []

    class BrowserFake:
        def __init__(
            self,
            content: str = "",
            trigger_by_action=None,
            set_of_marks=None,
            screenshot=None,
        ):
            self.content = content
            self.trigger_by_action = trigger_by_action
            self.set_of_marks = set_of_marks
            self.screenshot = screenshot

    class RecallFake:
        def __init__(
            self,
            recall_type=None,
            repo_name=None,
            repo_directory=None,
            repo_branch=None,
            date=None,
            runtime_hosts=None,
            additional_agent_instructions=None,
            custom_secrets_descriptions=None,
            working_dir=None,
            conversation_instructions=None,
            repo_instructions=None,
            microagent_knowledge=None,
        ):
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
            self.microagent_knowledge = microagent_knowledge

    class MicroagentFake:
        def __init__(self, name: str):
            self.name = name

    cm.MCPObservation = mcp_cls or MCPFake
    cm.IPythonRunCellObservation = ipy_cls or IPyFake
    cm.BrowserOutputObservation = browser_cls or BrowserFake
    cm.RecallObservation = recall_cls or RecallFake
    cm.MicroagentKnowledge = microagent_cls or MicroagentFake

    # Minimal RecallType object with attributes used in the module
    class RecallTypeFake:
        WORKSPACE_CONTEXT = getattr(recall_type, "WORKSPACE_CONTEXT", "WORKSPACE_CONTEXT")
        KNOWLEDGE = getattr(recall_type, "KNOWLEDGE", "KNOWLEDGE")

    cm.RecallType = RecallTypeFake


def _make_memory_instance(
    *,
    enable_prompt_extensions=True,
    disabled_microagents=None,
    is_valid_image_fn=None,
    prompt_manager=None,
):
    # Create a ConversationMemory instance without invoking its real __init__
    mem = object.__new__(cm.ConversationMemory)
    mem.agent_config = SimpleNamespace(
        enable_prompt_extensions=enable_prompt_extensions,
        disabled_microagents=disabled_microagents or [],
    )

    # Default simple prompt_manager with predictable returns
    class PM:
        def build_workspace_context(self, **kwargs):
            return "BUILT_WORKSPACE"

        def build_microagent_info(self, **kwargs):
            return "BUILT_MICROAGENT_INFO"

    mem.prompt_manager = prompt_manager or PM()

    # _is_valid_image_url determination
    mem._is_valid_image_url = is_valid_image_fn or (lambda url: bool(url))
    return mem


def test_mcp_observation_round_045():
    """MCPObservation should be converted into a user Message with its content."""
    _patch_basic_symbols()

    mem = _make_memory_instance()

    obs = cm.MCPObservation("some mcp content")

    tool_call_id_to_message = {}
    out = cm.ConversationMemory._process_observation(
        mem,
        obs,
        tool_call_id_to_message,
        max_message_chars=None,
        vision_is_active=False,
        enable_som_visual_browsing=False,
        current_index=0,
        events=None,
    )

    assert isinstance(out, list) and len(out) == 1
    msg = out[0]
    # role should be user
    assert getattr(msg, "role") == "user"
    # first content item should have text equal to the MCP content (truncate is identity)
    assert hasattr(msg, "content") and len(msg.content) >= 1
    first = msg.content[0]
    assert getattr(first, "text") == "some mcp content"


def test_browser_output_valid_and_invalid_image_round_045():
    """BrowserOutputObservation: valid image is added as ImageContent; invalid image adds explanatory text."""
    _patch_basic_symbols()

    # Case A: valid set_of_marks
    mem_valid = _make_memory_instance(is_valid_image_fn=lambda url: True)

    obs_valid = cm.BrowserOutputObservation(
        content="page text",
        trigger_by_action=cm.ActionType.BROWSE_INTERACTIVE,
        set_of_marks="http://valid/mark.png",
        screenshot=None,
    )

    out_valid = cm.ConversationMemory._process_observation(
        mem_valid,
        obs_valid,
        {},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=None,
    )

    assert len(out_valid) == 1
    msg_valid = out_valid[0]
    # Expect two content entries: TextContent then ImageContent
    assert len(msg_valid.content) >= 2
    img = msg_valid.content[1]
    assert getattr(img, "image_urls") == ["http://valid/mark.png"]

    # Case B: invalid screenshot should add explanatory note to first text content
    mem_invalid = _make_memory_instance(is_valid_image_fn=lambda url: False)

    obs_invalid = cm.BrowserOutputObservation(
        content="page text",
        trigger_by_action=cm.ActionType.BROWSE_INTERACTIVE,
        set_of_marks=None,
        screenshot="http://bad/image.png",
    )

    out_invalid = cm.ConversationMemory._process_observation(
        mem_invalid,
        obs_invalid,
        {},
        max_message_chars=None,
        vision_is_active=True,
        enable_som_visual_browsing=True,
        current_index=0,
        events=None,
    )

    assert len(out_invalid) == 1
    msg_invalid = out_invalid[0]
    assert len(msg_invalid.content) >= 1
    text0 = msg_invalid.content[0].text
    # Should mention that the screenshot was invalid/filtered
    assert "Note: The screenshot for this webpage was invalid or empty" in text0


def test_recall_workspace_with_microagents_round_045():
    """RecallObservation with WORKSPACE_CONTEXT and microagent knowledge should produce combined workspace + microagent message."""
    # Patch symbols and ensure deterministic prompt manager outputs
    _patch_basic_symbols()

    # Prepare prompt manager with predictable outputs
    class PM:
        def build_workspace_context(self, **kwargs):
            # return a recognizable string including whether conversation_instructions was passed
            return "WORKSPACE_CTX:built"

        def build_microagent_info(self, **kwargs):
            return "MICROAGENT:built"

    mem = _make_memory_instance(prompt_manager=PM(), disabled_microagents=[])

    # Create a recall observation of WORKSPACE_CONTEXT with conversation_instructions and microagent_knowledge
    recall_type_val = cm.RecallType.WORKSPACE_CONTEXT
    agent = cm.MicroagentKnowledge("agent_one")

    obs = cm.RecallObservation(
        recall_type=recall_type_val,
        repo_name=None,
        repo_directory=None,
        date=None,
        runtime_hosts=None,
        additional_agent_instructions=None,
        custom_secrets_descriptions=None,
        working_dir=None,
        conversation_instructions="Some instructions",
        repo_instructions="",
        microagent_knowledge=[agent],
    )

    out = cm.ConversationMemory._process_observation(
        mem,
        obs,
        {},
        max_message_chars=None,
        vision_is_active=False,
        enable_som_visual_browsing=False,
        current_index=0,
        events=None,
    )

    # Expected a single message combining workspace and microagent info
    assert len(out) == 1
    msg = out[0]
    assert getattr(msg, "role") == "user"
    # Content should include workspace text then microagent text
    texts = [c.text for c in msg.content]
    assert "WORKSPACE_CTX:built" in texts[0]
    assert any("MICROAGENT:built" in t for t in texts)
