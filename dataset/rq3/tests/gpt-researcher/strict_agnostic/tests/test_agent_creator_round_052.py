import asyncio
import json
import types
import pytest

import gpt_researcher.actions.agent_creator as agent_creator
from gpt_researcher.actions.agent_creator import handle_json_error

# Expected default returned by handle_json_error when nothing can be parsed
_EXPECTED_DEFAULT = (
    "Default Agent",
    (
        "You are an AI critical thinker research assistant. Your sole purpose is to write well written, "
        "critically acclaimed, objective and structured reports on given text."
    ),
)


def test_json_repair_success_round_052(monkeypatch):
    """Case: json_repair.loads returns a dict with both keys -> direct return.

    Covers lines where json_repair successfully returns agent_dict and the
    function returns agent_dict['server'], agent_dict['agent_role_prompt'].
    """
    monkeypatch.setattr(
        agent_creator,
        "json_repair",
        types.SimpleNamespace(loads=lambda response: {"server": "S1", "agent_role_prompt": "R1"}),
    )

    # No regex extraction should be needed here, but set a sentinel to ensure not used.
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda r: None)

    result = asyncio.run(handle_json_error("some irrelevant response"))
    assert result == ("S1", "R1")


def test_json_repair_raises_and_regex_valid_round_052(monkeypatch):
    """Case: json_repair.loads raises, response is truthy, regex returns valid JSON -> parse and return.

    Exercises the except branch, the code path when response is truthy (debug log path),
    and the regex-extraction + json.loads success path.
    """

    def fake_loads(_):
        raise ValueError("simulated json_repair failure")

    monkeypatch.setattr(agent_creator, "json_repair", types.SimpleNamespace(loads=fake_loads))

    # Provide a JSON string that json.loads can parse
    json_payload = json.dumps({"server": "S2", "agent_role_prompt": "R2"})
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda r: json_payload)

    result = asyncio.run(handle_json_error("some non-json text but truthy"))
    assert result == ("S2", "R2")


def test_json_repair_raises_and_regex_invalid_round_052(monkeypatch):
    """Case: json_repair.loads raises, regex returns invalid JSON -> fallback to default agent.

    Exercises the branch where json.loads on the extracted string raises JSONDecodeError
    and the fallback default is returned.
    """

    def fake_loads(_):
        raise RuntimeError("another simulated failure")

    monkeypatch.setattr(agent_creator, "json_repair", types.SimpleNamespace(loads=fake_loads))

    # Provide an invalid JSON string to trigger json.JSONDecodeError
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda r: '{"server": "S3", "agent_role_prompt": ')

    result = asyncio.run(handle_json_error("text that triggered repair failure"))
    assert result == _EXPECTED_DEFAULT


def test_json_repair_returns_missing_keys_and_no_regex_round_052(monkeypatch):
    """Case: json_repair.loads returns dict missing keys -> extract_json_with_regex returns None -> fallback.

    Exercises the path where json_repair does not raise but returns a dict without the needed keys,
    so the function proceeds to attempt regex extraction and ultimately falls back.
    """
    monkeypatch.setattr(
        agent_creator,
        "json_repair",
        types.SimpleNamespace(loads=lambda response: {"not_server": "x"}),
    )

    # No JSON found by regex extraction
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda r: None)

    result = asyncio.run(handle_json_error("ignored"))
    assert result == _EXPECTED_DEFAULT


def test_json_repair_raises_and_response_falsy_round_052(monkeypatch):
    """Case: json_repair.loads raises and response is falsy -> ensure fallback path when no regex extracted.

    Exercises except branch with response falsy (skipping debug logging) and no regex result,
    arriving at the default fallback.
    """

    def fake_loads(_):
        raise Exception("boom")

    monkeypatch.setattr(agent_creator, "json_repair", types.SimpleNamespace(loads=fake_loads))

    # No JSON extracted
    monkeypatch.setattr(agent_creator, "extract_json_with_regex", lambda r: None)

    result = asyncio.run(handle_json_error(None))
    assert result == _EXPECTED_DEFAULT
