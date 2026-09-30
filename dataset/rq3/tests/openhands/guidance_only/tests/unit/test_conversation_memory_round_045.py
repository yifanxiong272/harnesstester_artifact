import importlib
import pytest


# The tests below patch the conversation_memory module's observation classes
# with lightweight dummy types so isinstance checks inside
# ConversationMemory._process_observation work deterministically and without
# importing the full event/observation dependency graph.

class DummyMCPObservation:
    def __init__(self, content):
        self.content = content


class DummyIPythonRunCellObservation:
    def __init__(self, content, image_urls=None):
        self.content = content
        self.image_urls = image_urls or []


class DummyBrowserOutputObservation:
    def __init__(self, content, trigger_by_action, set_of_marks=None, screenshot=None):
        self.content = content
        self.trigger_by_action = trigger_by_action
        self.set_of_marks = set_of_marks
        self.screenshot = screenshot


class DummyLoopDetectionObservation:
    pass


class DummyRecallObservation:
    def __init__(
        self,
        recall_type,
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
        self.microagent_knowledge = microagent_knowledge or []


class DummyMicroagentKnowledge:
    def __init__(self, name):
        self.name = name


class DummyToolCallMetadata:
    def __init__(self, tool_call_id, function_name):
        self.tool_call_id = tool_call_id
        self.function_name = function_name


class SimplePromptManager:
    def __init__(self):
        self.built_workspace = False
        self.built_microagent = False

    def build_workspace_context(
        self, repository_info=None, runtime_info=None, conversation_instructions=None, repo_instructions=None
    ):
        self.built_workspace = True
        return "WORKSPACE_CTX"

    def build_microagent_info(self, triggered_agents=None):
        self.built_microagent = True
        # return a deterministic joined representation
        names = [a.name for a in (triggered_agents or [])]
        return "MICRO:" + ",".join(names)


class SimpleAgentConfig:
    def __init__(self, enable_prompt_extensions=False, disabled_microagents=None):
        self.enable_prompt_extensions = enable_prompt_extensions
        self.disabled_microagents = disabled_microagents or []


@pytest.fixture(autouse=True)
def import_module_and_patch(monkeypatch):
    """Import the target module and patch its observation class names to our
    lightweight dummy classes so isinstance checks are predictable."""
    cm_mod = importlib.import_module("openhands.memory.conversation_memory")

    # Patch the module-level observation names used by _process_observation
    monkeypatch.setattr(cm_mod, "MCPObservation", DummyMCPObservation)
    monkeypatch.setattr(cm_mod, "IPythonRunCellObservation", DummyIPythonRunCellObservation)
    monkeypatch.setattr(cm_mod, "BrowserOutputObservation", DummyBrowserOutputObservation)
    monkeypatch.setattr(cm_mod, "LoopDetectionObservation", DummyLoopDetectionObservation)
    monkeypatch.setattr(cm_mod, "RecallObservation", DummyRecallObservation)

    return cm_mod


def test_mcp_observation_round_045(import_module_and_patch):
    cm_mod = import_module_and_patch
    # Build a minimal ConversationMemory with deterministic prompt manager and config
    config = SimpleAgentConfig()
    prompt_manager = SimplePromptManager()
    cm = cm_mod.ConversationMemory(config, prompt_manager)

    obs = DummyMCPObservation(content="mcp content here")
    tool_call_map = {}

    result = cm._process_observation(obs, tool_call_map, max_message_chars=None)

    assert isinstance(result, list) and len(result) == 1
    msg = result[0]
    assert getattr(msg, "role") == "user"
    # The first content element should be a TextContent and contain the original string
    first = msg.content[0]
    assert hasattr(first, "text")
    assert "mcp content here" in first.text


def test_ipython_runcell_image_filtering_round_045(import_module_and_patch):
    cm_mod = import_module_and_patch
    config = SimpleAgentConfig()
    prompt_manager = SimplePromptManager()
    cm = cm_mod.ConversationMemory(config, prompt_manager)

    # Create content that includes a base64 image line and some normal text
    base64_line = "![image](data:image/png;base64,AAAA)"
    other_text = "Line after image"
    cell_text = base64_line + "\n" + other_text

    # Mixed image URLs: one valid, one empty/invalid
    obs = DummyIPythonRunCellObservation(content=cell_text, image_urls=["http://valid.img/1.png", ""])

    # Make _is_valid_image_url return True only for the first URL
    def is_valid(url):
        return bool(url)

    cm._is_valid_image_url = is_valid

    result = cm._process_observation(obs, {}, max_message_chars=None, vision_is_active=True)

    assert len(result) == 1
    msg = result[0]
    # Expect both a TextContent and an ImageContent because one URL was valid
    assert any(type(c).__name__ == "ImageContent" for c in msg.content)
    # The text content should have the base64 placeholder replaced
    text_contents = [c for c in msg.content if type(c).__name__ == "TextContent"]
    assert text_contents, "no TextContent found"
    text_val = text_contents[0].text
    assert "already displayed to user" in text_val
    # And there should be a note about filtered invalid images when vision_is_active == True
    assert "invalid or empty image(s)" in text_val


def test_browser_output_no_image_round_045(import_module_and_patch):
    cm_mod = import_module_and_patch
    config = SimpleAgentConfig()
    prompt_manager = SimplePromptManager()
    cm = cm_mod.ConversationMemory(config, prompt_manager)

    # Create a BrowserOutputObservation that represents an interactive browse with no images
    obs = DummyBrowserOutputObservation(
        content="page text here",
        trigger_by_action=cm_mod.ActionType.BROWSE_INTERACTIVE,
        set_of_marks=None,
        screenshot=None,
    )

    # Ensure the instance reports no valid images
    cm._is_valid_image_url = lambda url: False

    result = cm._process_observation(obs, {}, max_message_chars=None, vision_is_active=True, enable_som_visual_browsing=True)

    assert len(result) == 1
    msg = result[0]
    text_contents = [c for c in msg.content if type(c).__name__ == "TextContent"]
    assert text_contents, "expected a TextContent"
    text_val = text_contents[0].text
    # When no image is available and vision is active, a specific note is appended
    assert "No visual information (screenshot or set of marks) is available" in text_val


def test_recall_workspace_and_microagent_round_045(import_module_and_patch):
    cm_mod = import_module_and_patch
    # enable prompt extensions so workspace recall branch is taken
    config = SimpleAgentConfig(enable_prompt_extensions=True, disabled_microagents=[])
    prompt_manager = SimplePromptManager()
    cm = cm_mod.ConversationMemory(config, prompt_manager)

    # Create a recall observation with workspace context pieces and microagent knowledge
    micro_agents = [DummyMicroagentKnowledge(name="agentA"), DummyMicroagentKnowledge(name="agentB")]

    obs = DummyRecallObservation(
        recall_type=cm_mod.RecallType.WORKSPACE_CONTEXT,
        repo_name="repo",
        repo_directory="/some/dir",
        date="2026-01-01",
        runtime_hosts=['host1'],
        additional_agent_instructions=None,
        conversation_instructions="some convo instr",
        repo_instructions="do this",
        microagent_knowledge=micro_agents,
    )

    # Ensure ConversationMemory filters none of the microagents (disabled list empty)
    result = cm._process_observation(obs, {}, max_message_chars=None)

    # We expect a single message containing workspace context and microagent info
    assert isinstance(result, list) and len(result) == 1
    msg = result[0]
    # Should have two TextContent entries: one from workspace template and one from microagent template
    text_contents = [c for c in msg.content if type(c).__name__ == "TextContent"]
    assert len(text_contents) >= 1
    # The workspace builder returns a deterministic token, and microagent builder returns MICRO:...
    texts = [t.text for t in text_contents]
    assert any("WORKSPACE_CTX" in t for t in texts)
    assert any("MICRO:agentA" in t or "MICRO:agentB" in t for t in texts)


def test_recall_knowledge_microagent_round_045(import_module_and_patch):
    cm_mod = import_module_and_patch
    config = SimpleAgentConfig(enable_prompt_extensions=True, disabled_microagents=[])
    prompt_manager = SimplePromptManager()
    cm = cm_mod.ConversationMemory(config, prompt_manager)

    # For KNOWLEDGE recall we patch the instance method that filters agents so we can
    # deterministically return a non-empty list of triggered agents
    dummy_agents = [DummyMicroagentKnowledge(name="knowledge_agent")]

    def fake_filter(obs, current_index, events):
        return dummy_agents

    monkeypatch_target = importlib.import_module("openhands.memory.conversation_memory")
    # Patch the instance method on this instance only
    cm._filter_agents_in_microagent_obs = lambda obs, current_index, events: dummy_agents

    obs = DummyRecallObservation(recall_type=cm_mod.RecallType.KNOWLEDGE)

    result = cm._process_observation(obs, {}, max_message_chars=None)

    assert isinstance(result, list) and len(result) == 1
    msg = result[0]
    # The prompt manager returns "MICRO:..." for microagent info
    text_contents = [c for c in msg.content if type(c).__name__ == "TextContent"]
    assert text_contents and "MICRO:knowledge_agent" in text_contents[0].text


def test_loop_detection_observation_returns_empty_round_045(import_module_and_patch):
    cm_mod = import_module_and_patch
    config = SimpleAgentConfig()
    prompt_manager = SimplePromptManager()
    cm = cm_mod.ConversationMemory(config, prompt_manager)

    obs = DummyLoopDetectionObservation()
    result = cm._process_observation(obs, {}, max_message_chars=None)
    assert result == []
