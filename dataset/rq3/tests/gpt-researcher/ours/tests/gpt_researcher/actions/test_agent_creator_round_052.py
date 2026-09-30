import asyncio
import json
import logging
from types import SimpleNamespace

import pytest

from gpt_researcher.actions import agent_creator


def test_handle_json_error_json_repair_success_round_052():
    """If json_repair.loads returns a dict with the expected keys, the function should return them."""
    # Patch json_repair to return a valid dict
    class FakeJsonRepair:
        @staticmethod
        def loads(response):
            return {"server": "ServerX", "agent_role_prompt": "RoleX"}

    original = agent_creator.json_repair
    agent_creator.json_repair = FakeJsonRepair
    try:
        result = asyncio.run(agent_creator.handle_json_error("garbage but ignored"))
        assert result == ("ServerX", "RoleX")
    finally:
        agent_creator.json_repair = original


def test_handle_json_error_json_repair_raises_and_regex_succeeds_round_052(caplog):
    """When json_repair.loads raises and a regex extraction yields valid JSON, the extracted JSON should be used."""
    # Patch json_repair to raise
    class RaisingJsonRepair:
        @staticmethod
        def loads(response):
            raise RuntimeError("repair failed")

    # Ensure extract_json_with_regex returns JSON string
    monkey_json = '{"server": "ExtractedServer", "agent_role_prompt": "ExtractedRole"}'

    original_json_repair = agent_creator.json_repair
    original_extract = agent_creator.extract_json_with_regex
    agent_creator.json_repair = RaisingJsonRepair
    agent_creator.extract_json_with_regex = lambda r: monkey_json

    try:
        caplog.set_level(logging.WARNING)
        result = asyncio.run(agent_creator.handle_json_error("some response text"))
        # Should have used extracted JSON
        assert result == ("ExtractedServer", "ExtractedRole")
        # Because json_repair raised, a warning should have been logged about failing to parse
        assert any("Failed to parse agent JSON with json_repair" in rec.getMessage() for rec in caplog.records)
        # Also, because response was provided (truthy), debug with response slice is possible; ensure no crash occurred
    finally:
        agent_creator.json_repair = original_json_repair
        agent_creator.extract_json_with_regex = original_extract


def test_handle_json_error_regex_invalid_json_fallback_round_052(caplog):
    """If regex extraction yields invalid JSON, code should log a JSON decode warning and return the default agent."""
    class RaisingJsonRepair:
        @staticmethod
        def loads(response):
            raise ValueError("boom")

    # Extracted string is invalid JSON to trigger json.JSONDecodeError
    bad_json = '{"server": "BadServer", "agent_role_prompt": BAD'

    original_json_repair = agent_creator.json_repair
    original_extract = agent_creator.extract_json_with_regex
    agent_creator.json_repair = RaisingJsonRepair
    agent_creator.extract_json_with_regex = lambda r: bad_json

    try:
        caplog.set_level(logging.WARNING)
        result = asyncio.run(agent_creator.handle_json_error("irrelevant response"))
        # Should fall back to default agent when regex JSON cannot be decoded
        assert result[0] == "Default Agent"
        assert isinstance(result[1], str)
        assert "critical thinker" in result[1]
        # Confirm that a warning was logged about failing to decode JSON from regex extraction
        assert any("Failed to decode JSON from regex extraction" in rec.getMessage() for rec in caplog.records)
    finally:
        agent_creator.json_repair = original_json_repair
        agent_creator.extract_json_with_regex = original_extract


def test_handle_json_error_no_response_and_no_extraction_round_052(caplog):
    """When json_repair fails and there's no response (falsy) and regex finds nothing, it should silently fall back to default agent."""
    class RaisingJsonRepair:
        @staticmethod
        def loads(response):
            raise ValueError("boom")

    original_json_repair = agent_creator.json_repair
    original_extract = agent_creator.extract_json_with_regex
    agent_creator.json_repair = RaisingJsonRepair
    agent_creator.extract_json_with_regex = lambda r: None

    try:
        caplog.set_level(logging.INFO)
        # Pass response as None to hit the branch that does NOT log the debug of the response
        result = asyncio.run(agent_creator.handle_json_error(None))
        assert result[0] == "Default Agent"
        assert "You are an AI critical thinker" in result[1]
        # Should log info about falling back to default agent
        assert any("No valid JSON found in LLM response. Falling back to default agent." in rec.getMessage() for rec in caplog.records)
        # Ensure that there is no debug record mentioning LLM response (response was None so that branch is skipped)
        assert not any("LLM response that failed to parse" in rec.getMessage() for rec in caplog.records)
    finally:
        agent_creator.json_repair = original_json_repair
        agent_creator.extract_json_with_regex = original_extract
