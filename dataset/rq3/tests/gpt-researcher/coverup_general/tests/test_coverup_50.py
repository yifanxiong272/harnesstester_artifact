# file: multi_agents_ag2/agents/orchestrator.py:137-163
# asked: {"lines": [137, 138, 139, 140, 143, 144, 145, 146, 149, 150, 151, 152, 153, 154, 155, 157, 158, 159, 161, 163], "branches": [[150, 151], [150, 163], [154, 155], [154, 157]]}
# gained: {"lines": [137, 138, 139, 140, 143, 144, 145, 146, 149, 150, 151, 152, 153, 154, 155, 157, 158, 159, 161, 163], "branches": [[150, 151], [154, 155], [154, 157]]}

import sys
import types
import pytest

@pytest.mark.asyncio
async def test_run_section_immediate_review_none(monkeypatch):
    # Provide a fake 'autogen' module so importing orchestrator doesn't fail.
    fake_autogen = types.ModuleType("autogen")
    class Dummy:
        pass
    fake_autogen.ConversableAgent = Dummy
    fake_autogen.GroupChat = Dummy
    fake_autogen.GroupChatManager = Dummy
    fake_autogen.UserProxyAgent = Dummy
    monkeypatch.setitem(sys.modules, "autogen", fake_autogen)

    # Import after inserting the fake module
    from multi_agents_ag2.agents.orchestrator import ChiefEditorAgent

    # Create an instance without running __init__ to avoid side effects.
    agent = object.__new__(ChiefEditorAgent)
    agent.task = {"max_revisions": 3}
    logs = []

    async def fake_log(agent_key, message, stream_tag="logs"):
        logs.append((agent_key, message, stream_tag))

    agent._log = fake_log

    class R:
        async def run_depth_research(self, payload):
            assert "task" in payload and "topic" in payload and "title" in payload
            return {"draft": "initial draft text"}

    class Rv:
        async def run(self, draft_state):
            return {"review": None}

    class Re:
        async def run(self, payload):
            raise AssertionError("reviser.run should not be called when reviewer returns None")

    agents = {
        "research": R(),
        "reviewer": Rv(),
        "reviser": Re(),
    }

    result = await agent._run_section(agents, topic="T", title="Title")
    assert result == "initial draft text"
    assert any(k == "researcher" and "Running in depth research" in m for k, m, _ in logs)
    assert any(k == "reviewer" and "Reviewing draft" in m for k, m, _ in logs)


@pytest.mark.asyncio
async def test_run_section_with_revision_then_stop(monkeypatch):
    # Provide a fake 'autogen' module so importing orchestrator doesn't fail.
    fake_autogen = types.ModuleType("autogen")
    class Dummy:
        pass
    fake_autogen.ConversableAgent = Dummy
    fake_autogen.GroupChat = Dummy
    fake_autogen.GroupChatManager = Dummy
    fake_autogen.UserProxyAgent = Dummy
    monkeypatch.setitem(sys.modules, "autogen", fake_autogen)

    from multi_agents_ag2.agents.orchestrator import ChiefEditorAgent

    agent = object.__new__(ChiefEditorAgent)
    agent.task = {"max_revisions": 5}
    logs = []

    async def fake_log(agent_key, message, stream_tag="logs"):
        logs.append((agent_key, message, stream_tag))

    agent._log = fake_log

    class R:
        async def run_depth_research(self, payload):
            return {"draft": "original draft"}

    reviewer_calls = {"count": 0}

    class Rv:
        async def run(self, draft_state):
            reviewer_calls["count"] += 1
            if reviewer_calls["count"] == 1:
                assert draft_state.get("draft") == "original draft"
                return {"review": "please expand section 2"}
            return {"review": None}

    class Re:
        async def run(self, payload):
            assert "review" in payload and payload["review"] == "please expand section 2"
            return {"draft": "revised draft v1", "revision_notes": "expanded section 2"}

    agents = {
        "research": R(),
        "reviewer": Rv(),
        "reviser": Re(),
    }

    result = await agent._run_section(agents, topic="SomeTopic", title="SomeTitle")
    assert result == "revised draft v1"
    assert reviewer_calls["count"] >= 2
    assert any("Reviewing draft" in m and k == "reviewer" for k, m, _ in logs)
    assert any("Revising draft" in m and k == "reviser" for k, m, _ in logs)
