# file: gpt_researcher/actions/agent_creator.py:65-107
# asked: {"lines": [78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 103, 104], "branches": [[80, 81], [80, 92], [89, 90], [89, 92], [93, 94], [93, 103]]}
# gained: {"lines": [78, 79, 80, 82, 83, 84, 85, 86, 87, 89, 90, 92, 93, 94, 95, 96, 97, 98, 99, 100, 103, 104], "branches": [[80, 92], [89, 90], [93, 94], [93, 103]]}

import importlib
import json
import pytest

# Import the module under test
mod = importlib.import_module("gpt_researcher.actions.agent_creator")
handle_json_error = mod.handle_json_error

DEFAULT_AGENT = (
    "Default Agent",
    (
        "You are an AI critical thinker research assistant. Your sole purpose is to write well written, "
        "critically acclaimed, objective and structured reports on given text."
    ),
)


@pytest.mark.asyncio
async def test_json_repair_raises_then_regex_returns_valid(monkeypatch):
    called = {}

    # Make json_repair.loads raise an exception to exercise the except branch
    def fake_json_repair_loads(value):
        called["json_repair_arg"] = value
        raise ValueError("json_repair broken")

    monkeypatch.setattr(mod, "json_repair", type("JR", (), {"loads": staticmethod(fake_json_repair_loads)}))

    # Provide a valid JSON string via regex extraction
    def fake_extract_json_with_regex(value):
        called["regex_arg"] = value
        return json.dumps({"server": "Recovered Agent", "agent_role_prompt": "Recovered Role"})

    monkeypatch.setattr(mod, "extract_json_with_regex", fake_extract_json_with_regex)

    response_text = "some malformed response from LLM"
    result = await handle_json_error(response_text)

    assert result == ("Recovered Agent", "Recovered Role")
    assert called["json_repair_arg"] == response_text
    assert called["regex_arg"] == response_text


@pytest.mark.asyncio
async def test_json_repair_raises_then_regex_returns_malformed_logs_and_falls_back(monkeypatch, caplog):
    # json_repair.loads raises to hit except block
    def fake_json_repair_loads(value):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "json_repair", type("JR", (), {"loads": staticmethod(fake_json_repair_loads)}))

    # extract_json_with_regex returns malformed JSON so json.loads will raise JSONDecodeError
    def fake_extract_json_with_regex(value):
        return '{"server": "S", "agent_role_prompt": "P" '  # missing closing brace

    monkeypatch.setattr(mod, "extract_json_with_regex", fake_extract_json_with_regex)

    caplog.clear()
    caplog.set_level("WARNING")

    result = await handle_json_error("some response")

    # Should fall back to default agent when json.loads fails
    assert result == DEFAULT_AGENT

    # Ensure a warning about failed decode was logged
    found = any("Failed to decode JSON from regex extraction" in rec.message for rec in caplog.records)
    assert found, "Expected a warning about JSON decode failure in logs"


@pytest.mark.asyncio
async def test_json_repair_returns_dict_missing_keys_then_fallback(monkeypatch):
    calls = {}

    # json_repair.loads returns a dict but missing required keys -> should continue to regex
    def fake_json_repair_loads(value):
        calls["json_repair_arg"] = value
        return {"not_server": "x"}  # missing 'server' and 'agent_role_prompt'

    monkeypatch.setattr(mod, "json_repair", type("JR", (), {"loads": staticmethod(fake_json_repair_loads)}))

    # regex extractor returns None -> final fallback
    def fake_extract_json_with_regex(value):
        calls["regex_arg"] = value
        return None

    monkeypatch.setattr(mod, "extract_json_with_regex", fake_extract_json_with_regex)

    result = await handle_json_error("irrelevant")

    assert result == DEFAULT_AGENT
    assert calls["json_repair_arg"] == "irrelevant"
    assert calls["regex_arg"] == "irrelevant"
