import pytest
from types import SimpleNamespace

from openhands.memory.conversation_memory import ConversationMemory
from openhands.events.observation.mcp import MCPObservation
from openhands.events.observation import (
    BrowserOutputObservation,
    FileDownloadObservation,
    LoopDetectionObservation,
)
from openhands.core.schema import ActionType
from openhands.core.message import Message, TextContent


class DummyPromptManager:
    def build_workspace_context(self, **kwargs):
        return "workspace-context"

    def build_microagent_info(self, **kwargs):
        return "microagent-info"


def _make_conv():
    """Create a ConversationMemory-like instance without calling __init__.

    We bypass __init__ to deterministically set only the attributes used by
    _process_observation in these tests.
    """
    conv = ConversationMemory.__new__(ConversationMemory)
    conv.prompt_manager = DummyPromptManager()
    # Minimal agent_config expected fields used in the code paths we exercise
    conv.agent_config = SimpleNamespace(enable_prompt_extensions=True, disabled_microagents=set())
    return conv


def test_browser_output_round_045():
    conv = _make_conv()

    # Build a BrowserOutputObservation instance without invoking its constructor
    obs = object.__new__(BrowserOutputObservation)
    obs.content = "Some webpage text"
    obs.trigger_by_action = ActionType.BROWSE_INTERACTIVE
    # No set_of_marks, provide a screenshot that will be considered invalid
    obs.set_of_marks = None
    obs.screenshot = "not_a_valid_url"

    # Force deterministic behavior: mark any url as invalid
    conv._is_valid_image_url = lambda url: False

    out = conv._process_observation(
        obs, tool_call_id_to_message={}, max_message_chars=None, vision_is_active=True, enable_som_visual_browsing=True
    )

    # We should get a single user message with explanatory note about the invalid screenshot
    assert isinstance(out, list) and len(out) == 1
    msg = out[0]
    assert isinstance(msg, Message)
    # First content element is TextContent and should contain the explanatory note
    first_text = msg.content[0].text
    assert "Note: The screenshot for this webpage was invalid or empty and has been filtered" in first_text


def test_mcp_filedownload_loop_round_045():
    conv = _make_conv()

    # MCPObservation: should produce a user message with the given content
    mcp = object.__new__(MCPObservation)
    mcp.content = "mcp-content-123"
    out_mcp = conv._process_observation(mcp, tool_call_id_to_message={})
    assert isinstance(out_mcp, list) and len(out_mcp) == 1
    assert out_mcp[0].content[0].text == "mcp-content-123"

    # FileDownloadObservation: should produce a user message with the file content
    fd = object.__new__(FileDownloadObservation)
    fd.content = "downloaded-file-content"
    out_fd = conv._process_observation(fd, tool_call_id_to_message={})
    assert isinstance(out_fd, list) and len(out_fd) == 1
    assert out_fd[0].content[0].text == "downloaded-file-content"

    # LoopDetectionObservation: should be handled internally and return an empty list
    loop_obs = object.__new__(LoopDetectionObservation)
    out_loop = conv._process_observation(loop_obs, tool_call_id_to_message={})
    assert out_loop == []


def test_unknown_obs_round_045():
    conv = _make_conv()

    class UnknownObs:
        pass

    with pytest.raises(ValueError) as exc:
        conv._process_observation(UnknownObs(), tool_call_id_to_message={})

    assert "Unknown observation type" in str(exc.value)
