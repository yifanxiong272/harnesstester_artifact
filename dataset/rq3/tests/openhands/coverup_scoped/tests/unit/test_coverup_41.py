# file: openhands/memory/conversation_memory.py:354-694
# asked: {"lines": [412, 413, 485, 486, 494, 495, 498, 499, 500, 518, 519, 521, 522, 535, 536, 539, 575, 576, 597, 598, 599, 600, 627, 628, 629, 632, 679], "branches": [[410, 412], [450, 456], [472, 479], [484, 485], [493, 494], [501, 510], [517, 518], [520, 521], [534, 535], [537, 539], [574, 575], [595, 597], [626, 627], [639, 682], [656, 668], [669, 679]]}
# gained: {"lines": [412, 413, 485, 486, 494, 495, 498, 499, 500, 518, 519, 521, 522, 535, 536, 539, 575, 576, 597, 598, 599, 600, 627, 628, 629, 632, 679], "branches": [[410, 412], [472, 479], [484, 485], [493, 494], [517, 518], [520, 521], [534, 535], [537, 539], [574, 575], [595, 597], [626, 627], [669, 679]]}

import pytest
from types import SimpleNamespace

import openhands.memory.conversation_memory as conv_mod
from openhands.core.message import Message, TextContent, ImageContent
from openhands.events.recall_type import RecallType
from openhands.core.schema import ActionType


class DummyPromptManager:
    def build_workspace_context(self, repository_info=None, runtime_info=None, conversation_instructions=None, repo_instructions=""):
        return f"WORKSPACE_CTX:{repository_info}:{runtime_info}:{conversation_instructions}:{repo_instructions}"

    def build_microagent_info(self, triggered_agents=None):
        names = ",".join(a.name for a in (triggered_agents or []))
        return f"MICROAGENT_INFO:{names}"


@pytest.fixture
def conv():
    # Minimal agent_config object with attributes used by ConversationMemory
    agent_config = SimpleNamespace(enable_prompt_extensions=True, disabled_microagents=[])
    pm = DummyPromptManager()
    return conv_mod.ConversationMemory(agent_config, pm)


def make_fake_class(name, attrs=None):
    attrs = attrs or {}
    return type(name, (), attrs)


def test_mcp_observation_and_tool_call_metadata(monkeypatch, conv):
    # Monkeypatch MCPObservation in module to a fake class
    FakeMCP = make_fake_class(
        "FakeMCP",
        {
            "__init__": lambda self, content, tool_call_metadata=None: (setattr(self, "content", content), setattr(self, "tool_call_metadata", tool_call_metadata))[0]
        },
    )
    monkeypatch.setattr(conv_mod, "MCPObservation", FakeMCP)

    # Case: plain MCPObservation returns TextContent message
    obs = FakeMCP("mcp content here")
    msgs = conv._process_observation(obs, {}, max_message_chars=100)
    assert isinstance(msgs, list) and len(msgs) == 1
    msg = msgs[0]
    assert isinstance(msg, Message)
    assert isinstance(msg.content[0], TextContent)
    assert "mcp content here" in msg.content[0].text

    # Case: tool_call_metadata present -> stored as tool response and [] returned
    tool_meta = SimpleNamespace(tool_call_id="tc1", function_name="fn")
    obs_with_tool = FakeMCP("mcp content", tool_call_metadata=tool_meta)
    tool_map = {}
    res = conv._process_observation(obs_with_tool, tool_map, max_message_chars=100)
    assert res == []
    assert "tc1" in tool_map
    stored = tool_map["tc1"]
    assert stored.role == "tool"
    assert stored.tool_call_id == "tc1"
    assert stored.name == "fn"


def test_ipython_images_filtering(monkeypatch, conv):
    # Replace IPythonRunCellObservation
    FakeIPy = make_fake_class(
        "FakeIPy",
        {
            "__init__": lambda self, content, image_urls=None: (setattr(self, "content", content), setattr(self, "image_urls", image_urls or []))[0]
        },
    )
    monkeypatch.setattr(conv_mod, "IPythonRunCellObservation", FakeIPy)

    # Control validity checks: only 'http://valid.img' is valid
    monkeypatch.setattr(conv_mod.ConversationMemory, "_is_valid_image_url", staticmethod(lambda url: bool(url and url.startswith("http"))))

    # Case 1: some valid, some invalid -> should include ImageContent and note about filtered images
    obs = FakeIPy("line1\n![image](data:image/png;base64,AAA)\nline3", image_urls=["http://valid.img", ""])
    msgs = conv._process_observation(obs, {}, max_message_chars=1000, vision_is_active=True)
    assert len(msgs) == 1
    msg = msgs[0]
    assert any(isinstance(c, ImageContent) for c in msg.content)
    # Ensure explanatory note added because one invalid image was filtered
    txts = [c for c in msg.content if isinstance(c, TextContent)]
    assert txts and "invalid or empty image(s) were filtered" in txts[0].text

    # Case 2: image_urls present but none valid -> text note about all filtered (branch 450->456)
    obs2 = FakeIPy("content", image_urls=["bad1", ""])
    msgs2 = conv._process_observation(obs2, {}, max_message_chars=1000, vision_is_active=True)
    assert len(msgs2) == 1
    txt = msgs2[0].content[0]
    assert isinstance(txt, TextContent)
    assert "All 2 image(s) in this output were invalid or empty and have been filtered" in txt.text

    # Case 3: has base64 image line should be replaced in text (no URLs)
    obs3 = FakeIPy("line before\n![image](data:image/png;base64,BBBB)\nline after", image_urls=[])
    msgs3 = conv._process_observation(obs3, {}, max_message_chars=1000, vision_is_active=False)
    assert "already displayed to user" in msgs3[0].content[0].text


def test_browser_output_image_branches(monkeypatch, conv):
    # Fake BrowserOutputObservation
    def init_bs(self, content, trigger_by_action=None, set_of_marks=None, screenshot=None):
        self.content = content
        self.trigger_by_action = trigger_by_action
        self.set_of_marks = set_of_marks
        self.screenshot = screenshot

    FakeBrowser = make_fake_class("FakeBrowser", {"__init__": init_bs})
    monkeypatch.setattr(conv_mod, "BrowserOutputObservation", FakeBrowser)

    # Make image URL validity controllable
    monkeypatch.setattr(conv_mod.ConversationMemory, "_is_valid_image_url", staticmethod(lambda url: url == "http://good"))

    # Case A: set_of_marks present and valid -> ImageContent appended
    obsA = FakeBrowser("page text", trigger_by_action=ActionType.BROWSE_INTERACTIVE, set_of_marks="http://good", screenshot=None)
    msgsA = conv._process_observation(obsA, {}, max_message_chars=1000, vision_is_active=False, enable_som_visual_browsing=True)
    assert len(msgsA) == 1
    assert any(isinstance(c, ImageContent) for c in msgsA[0].content)

    # Case B: screenshot present but invalid -> vision_is_active True leads to warning text appended
    obsB = FakeBrowser("page text B", trigger_by_action=ActionType.BROWSE_INTERACTIVE, set_of_marks=None, screenshot="bad")
    msgsB = conv._process_observation(obsB, {}, max_message_chars=1000, vision_is_active=True, enable_som_visual_browsing=True)
    txtB = msgsB[0].content[0]
    assert isinstance(txtB, TextContent)
    assert "has been filtered" in txtB.text or "invalid or empty" in txtB.text

    # Case C: no images at all -> vision_is_active True should add "No visual information" note (branch 501->510)
    obsC = FakeBrowser("page text C", trigger_by_action=ActionType.BROWSE_INTERACTIVE, set_of_marks=None, screenshot=None)
    msgsC = conv._process_observation(obsC, {}, max_message_chars=1000, vision_is_active=True, enable_som_visual_browsing=True)
    txtC = msgsC[0].content[0]
    assert isinstance(txtC, TextContent)
    assert "No visual information" in txtC.text


def test_other_simple_observations_and_loop_handling(monkeypatch, conv):
    # AgentDelegateObservation, AgentThinkObservation, TaskTrackingObservation, FileEdit, FileRead, Error, UserReject, AgentCondensation, FileDownload, LoopDetection
    names = [
        "AgentDelegateObservation",
        "AgentThinkObservation",
        "TaskTrackingObservation",
        "FileEditObservation",
        "FileReadObservation",
        "ErrorObservation",
        "UserRejectObservation",
        "AgentCondensationObservation",
        "FileDownloadObservation",
        "LoopDetectionObservation",
    ]
    for n in names:
        if n == "FileEditObservation":
            # custom __str__ to return content so truncation/str conversion yields expected text
            def fe_init(self, content="X", outputs=None):
                self.content = content
                self.outputs = outputs or {}

            def fe_str(self):
                return str(self.content)

            cls = make_fake_class(n, {"__init__": fe_init, "__str__": fe_str})
        else:
            cls = make_fake_class(n, {"__init__": lambda self, content="X", outputs=None: (setattr(self, "content", content), setattr(self, "outputs", outputs or {}))[0]})
        monkeypatch.setattr(conv_mod, n, cls)

    # AgentDelegateObservation: uses outputs if present
    ad = conv_mod.AgentDelegateObservation("delegated", outputs={"content": "from outputs"})
    msgs = conv._process_observation(ad, {}, max_message_chars=1000)
    assert msgs and isinstance(msgs[0].content[0], TextContent)
    assert "from outputs" in msgs[0].content[0].text

    # AgentThinkObservation
    at = conv_mod.AgentThinkObservation("thinking here")
    msgs = conv._process_observation(at, {}, max_message_chars=1000)
    assert "thinking here" in msgs[0].content[0].text

    # TaskTrackingObservation
    tt = conv_mod.TaskTrackingObservation("tracking")
    msgs = conv._process_observation(tt, {}, max_message_chars=1000)
    assert "tracking" in msgs[0].content[0].text

    # FileEditObservation -> string conversion used
    fe = conv_mod.FileEditObservation("edited")
    msgs = conv._process_observation(fe, {}, max_message_chars=1000)
    assert "edited" in msgs[0].content[0].text

    # FileReadObservation content returned as-is
    fr = conv_mod.FileReadObservation("file content")
    msgs = conv._process_observation(fr, {}, max_message_chars=1000)
    assert "file content" in msgs[0].content[0].text

    # ErrorObservation adds error suffix
    err = conv_mod.ErrorObservation("oh no")
    msgs = conv._process_observation(err, {}, max_message_chars=1000)
    assert "[Error occurred in processing last action]" in msgs[0].content[0].text

    # UserRejectObservation adds rejection suffix
    ur = conv_mod.UserRejectObservation("bad")
    msgs = conv._process_observation(ur, {}, max_message_chars=1000)
    assert "[Last action has been rejected by the user]" in msgs[0].content[0].text

    # AgentCondensationObservation
    ac = conv_mod.AgentCondensationObservation("condense me")
    msgs = conv._process_observation(ac, {}, max_message_chars=1000)
    assert "condense me" in msgs[0].content[0].text

    # FileDownloadObservation
    fd = conv_mod.FileDownloadObservation("downloaded file")
    msgs = conv._process_observation(fd, {}, max_message_chars=1000)
    assert "downloaded file" in msgs[0].content[0].text

    # LoopDetectionObservation returns empty list
    ld = conv_mod.LoopDetectionObservation("looped")
    res = conv._process_observation(ld, {}, max_message_chars=1000)
    assert res == []


def test_recall_workspace_and_microagents(monkeypatch):
    # Setup ConversationMemory with a prompt manager that will provide workspace and microagent text
    agent_config = SimpleNamespace(enable_prompt_extensions=True, disabled_microagents=[])
    pm = DummyPromptManager()
    conv = conv_mod.ConversationMemory(agent_config, pm)

    # Create Fake RecallObservation class used for WORKSPACE_CONTEXT
    def init_recall(self, recall_type, repo_name=None, repo_directory=None, repo_branch=None, date="2023-01-01", runtime_hosts=None, additional_agent_instructions=None, custom_secrets_descriptions=None, working_dir=None, conversation_instructions=None, repo_instructions=None, microagent_knowledge=None):
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

    FakeRecall = make_fake_class("FakeRecall", {"__init__": init_recall})
    monkeypatch.setattr(conv_mod, "RecallObservation", FakeRecall)
    # Also need MicroagentKnowledge class shape for microagent list elements
    Micro = make_fake_class("Micro", {"__init__": lambda self, name: setattr(self, "name", name)})
    # Create observation containing repo info, conversation_instructions and microagent knowledge
    micro_agents = [Micro("a1"), Micro("a2")]
    obs = FakeRecall(RecallType.WORKSPACE_CONTEXT, repo_name="repo1", repo_directory="dir", repo_branch="main", conversation_instructions="please", repo_instructions="readme", microagent_knowledge=micro_agents)

    msgs = conv._process_observation(obs, {}, max_message_chars=1000)
    assert msgs and isinstance(msgs[0], Message)
    # Should contain workspace context text first then microagent info
    contents = msgs[0].content
    assert any(isinstance(c, TextContent) and "WORKSPACE_CTX" in c.text for c in contents)
    assert any(isinstance(c, TextContent) and "MICROAGENT_INFO" in c.text for c in contents)


def test_recall_knowledge_and_disable_extensions(monkeypatch, conv):
    # Prepare fake RecallObservation and microagents
    FakeRecall = make_fake_class("FakeRecall", {"__init__": lambda self, recall_type, microagent_knowledge=None: (setattr(self, "recall_type", recall_type), setattr(self, "microagent_knowledge", microagent_knowledge))[0]})
    monkeypatch.setattr(conv_mod, "RecallObservation", FakeRecall)
    Micro = make_fake_class("Micro", {"__init__": lambda self, name: setattr(self, "name", name)})

    # Test KNOWLEDGE path where _filter_agents_in_microagent_obs returns some agents
    obs_k = FakeRecall(RecallType.KNOWLEDGE, microagent_knowledge=[Micro("m1")])
    # Monkeypatch ConversationMemory._filter_agents_in_microagent_obs to return one agent
    monkeypatch.setattr(conv, "_filter_agents_in_microagent_obs", lambda obs, idx, events: [Micro("m1")])
    msgs = conv._process_observation(obs_k, {}, max_message_chars=1000, current_index=0, events=[])
    assert msgs and isinstance(msgs[0], Message)
    assert "MICROAGENT_INFO" in msgs[0].content[0].text

    # Test KNOWLEDGE path where _filter_agents_in_microagent_obs returns empty -> should return []
    monkeypatch.setattr(conv, "_filter_agents_in_microagent_obs", lambda obs, idx, events: [])
    msgs2 = conv._process_observation(obs_k, {}, max_message_chars=1000, current_index=0, events=[])
    assert msgs2 == []

    # If prompt extensions disabled, any RecallObservation returns []
    conv.agent_config.enable_prompt_extensions = False
    obs_any = FakeRecall(RecallType.KNOWLEDGE, microagent_knowledge=[Micro("m2")])
    res = conv._process_observation(obs_any, {}, max_message_chars=1000)
    assert res == []


def test_unknown_observation_raises(monkeypatch, conv):
    # Create a dummy class not matching any expected observation and ensure ValueError is raised
    class SomeUnknown:
        pass

    with pytest.raises(ValueError):
        conv._process_observation(SomeUnknown(), {}, max_message_chars=1000)
