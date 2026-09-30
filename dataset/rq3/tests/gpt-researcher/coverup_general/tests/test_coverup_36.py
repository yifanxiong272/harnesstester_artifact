# file: gpt_researcher/actions/agent_creator.py:65-107
# asked: {"lines": [78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 103, 104], "branches": [[80, 81], [80, 92], [89, 90], [89, 92], [93, 94], [93, 103]]}
# gained: {"lines": [78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 103, 104], "branches": [[80, 81], [89, 90], [93, 94]]}

import json
import pytest
from types import SimpleNamespace

import gpt_researcher.actions.agent_creator as agent_creator


@pytest.mark.asyncio
async def test_handle_json_error_repair_success(monkeypatch):
    # Arrange: make json_repair.loads return a dict with required keys
    returned = {"server": "RepairAgent", "agent_role_prompt": "You are repaired."}

    def fake_loads(resp):
        assert resp == "some response"
        return returned

    monkeypatch.setattr(agent_creator, "json_repair", SimpleNamespace(loads=fake_loads))

    # Act
    result = await agent_creator.handle_json_error("some response")

    # Assert
    assert result == ("RepairAgent", "You are repaired.")


@pytest.mark.asyncio
async def test_handle_json_error_repair_exception_then_regex_valid(monkeypatch):
    # Arrange: make json_repair.loads raise an exception
    def fake_loads(resp):
        raise ValueError("intentional failure")

    monkeypatch.setattr(agent_creator, "json_repair", SimpleNamespace(loads=fake_loads))

    # Make extract_json_with_regex return a good JSON string
    good_json = json.dumps({"server": "RegexAgent", "agent_role_prompt": "You are from regex."})
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda resp: good_json)

    # Act
    result = await agent_creator.handle_json_error("some malformed response")

    # Assert
    assert result == ("RegexAgent", "You are from regex.")


@pytest.mark.asyncio
async def test_handle_json_error_repair_exception_then_regex_invalid_fallback(monkeypatch):
    # Arrange: make json_repair.loads raise an exception
    def fake_loads(resp):
        raise RuntimeError("another failure")

    monkeypatch.setattr(agent_creator, "json_repair", SimpleNamespace(loads=fake_loads))

    # Make extract_json_with_regex return invalid JSON so json.loads raises JSONDecodeError
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda resp: "{not: valid, json}")

    # Act
    result = await agent_creator.handle_json_error("some other malformed response")

    # Assert fallback to default agent
    expected_prompt_start = "You are an AI critical thinker research assistant."
    assert result[0] == "Default Agent"
    assert isinstance(result[1], str)
    assert result[1].startswith(expected_prompt_start)
