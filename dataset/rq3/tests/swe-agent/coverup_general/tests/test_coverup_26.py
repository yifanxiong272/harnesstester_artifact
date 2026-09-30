# file: sweagent/run/run_traj_to_demo.py:35-56
# asked: {"lines": [35, 36, 37, 38, 39, 40, 41, 43, 45, 46, 47, 48, 49, 50, 51, 54, 55, 56], "branches": [[39, 40], [39, 41]]}
# gained: {"lines": [35, 36, 37, 38, 39, 40, 41, 43, 45, 46, 47, 48, 49, 50, 51, 54, 55, 56], "branches": [[39, 40], [39, 41]]}

import json
from pathlib import Path

import pytest

import sweagent.run.run_traj_to_demo as run_traj_mod


def _make_logger_catcher(calls):
    class Logger:
        def info(self, msg):
            calls.append(msg)
    return Logger()


def _make_save_demo_catcher(calls):
    def _save_demo(output_data, output_file, traj_path):
        calls.append((output_data, output_file, traj_path))
    return _save_demo


def _keys_of(item):
    return set(item.keys())


def test_convert_traj_to_action_demo_with_dict_replay_config(tmp_path, monkeypatch):
    # Prepare traj file with replay_config as dict and various history steps
    traj = {
        "replay_config": {"speed": 1, "mode": "test"},
        "history": [
            # should be included: assistant, default agent -> main, not is_demo
            {
                "role": "assistant",
                "content": "assistant message 1",
                "message_type": "reply",
                "extra_field": "should_be_removed",
            },
            # should be excluded: assistant but agent not main/primary
            {
                "role": "assistant",
                "content": "assistant message 2",
                "agent": "secondary",
                "message_type": "reply",
            },
            # should be excluded: user (include_user False)
            {
                "role": "user",
                "content": "user message",
                "message_type": "input",
            },
            # should be excluded: assistant but is_demo True
            {
                "role": "assistant",
                "content": "assistant demo",
                "is_demo": True,
                "message_type": "reply",
            },
            # should be included: assistant with agent primary and tool_calls/tool_call_ids preserved
            {
                "role": "assistant",
                "content": "assistant message 3",
                "agent": "primary",
                "tool_calls": [{"name": "tool1"}],
                "tool_call_ids": [123],
                "message_type": "reply",
                "other": "dropme",
            },
        ],
    }

    traj_path = tmp_path / "traj1.json"
    output_file = tmp_path / "out1.json"
    traj_path.write_text(json.dumps(traj))

    saved_calls = []
    log_calls = []

    # Patch save_demo and logger in the module under test
    monkeypatch.setattr(run_traj_mod, "save_demo", _make_save_demo_catcher(saved_calls))
    monkeypatch.setattr(run_traj_mod, "logger", _make_logger_catcher(log_calls))

    # Call function under test
    run_traj_mod.convert_traj_to_action_demo(traj_path, output_file, include_user=False)

    # Assertions: save_demo called exactly once
    assert len(saved_calls) == 1, "save_demo should be called once"
    output_data, saved_output_file, saved_traj_path = saved_calls[0]

    # replay_config should remain a dict (unchanged)
    assert isinstance(output_data["replay_config"], dict)
    assert output_data["replay_config"] == {"speed": 1, "mode": "test"}

    # filtered history should contain only the two included assistant steps (first and fifth)
    hist = output_data["history"]
    assert isinstance(hist, list)
    assert len(hist) == 2

    # Check contents and that only allowed keys are present
    allowed_keys = {"content", "role", "tool_calls", "agent", "message_type", "tool_call_ids"}
    for item in hist:
        assert item["role"] == "assistant"
        assert _keys_of(item).issubset(allowed_keys)
    # Check specific values preserved
    assert hist[0]["content"] == "assistant message 1"
    assert hist[1]["content"] == "assistant message 3"
    assert "other" not in hist[1]
    assert hist[1]["tool_calls"] == [{"name": "tool1"}]
    assert hist[1]["tool_call_ids"] == [123]

    # Check that save_demo received the correct file paths
    assert saved_output_file == output_file
    assert saved_traj_path == traj_path

    # Check logger.info was called with the saved message
    assert len(log_calls) == 1
    assert f"Saved demo to {output_file}" in log_calls[0]


def test_convert_traj_to_action_demo_with_string_replay_config_and_include_user(tmp_path, monkeypatch):
    # Prepare traj file with replay_config as JSON string and include_user True
    replay_cfg = {"alpha": 0.5, "name": "string_cfg"}
    traj = {
        "replay_config": json.dumps(replay_cfg),
        "history": [
            # user: should be included (include_user True)
            {
                "role": "user",
                "content": "user message 1",
                "message_type": "input",
                # no agent -> default main
            },
            # tool: should be included
            {
                "role": "tool",
                "content": "tool output",
                "agent": "primary",
                "tool_calls": [{"name": "toolX"}],
                "message_type": "tool_resp",
            },
            # assistant: should be included
            {
                "role": "assistant",
                "content": "assistant here",
                "agent": "main",
                "message_type": "reply",
            },
            # should be excluded: tool with agent not main/primary
            {
                "role": "tool",
                "content": "tool other",
                "agent": "secondary",
                "message_type": "tool_resp",
            },
            # should be excluded: user but is_demo True
            {
                "role": "user",
                "content": "user demo",
                "is_demo": True,
                "message_type": "input",
            },
        ],
    }

    traj_path = tmp_path / "traj2.json"
    output_file = tmp_path / "out2.json"
    traj_path.write_text(json.dumps(traj))

    saved_calls = []
    log_calls = []

    monkeypatch.setattr(run_traj_mod, "save_demo", _make_save_demo_catcher(saved_calls))
    monkeypatch.setattr(run_traj_mod, "logger", _make_logger_catcher(log_calls))

    # Call function with include_user True
    run_traj_mod.convert_traj_to_action_demo(traj_path, output_file, include_user=True)

    # Assertions
    assert len(saved_calls) == 1
    output_data, saved_output_file, saved_traj_path = saved_calls[0]

    # replay_config should be parsed from JSON string to dict
    assert isinstance(output_data["replay_config"], dict)
    assert output_data["replay_config"] == replay_cfg

    hist = output_data["history"]
    # Expect user, tool, assistant included (but not the excluded ones)
    assert len(hist) == 3

    roles = [item["role"] for item in hist]
    assert "user" in roles
    assert "tool" in roles
    assert "assistant" in roles

    # Ensure allowed keys only
    allowed_keys = {"content", "role", "tool_calls", "agent", "message_type", "tool_call_ids"}
    for item in hist:
        assert _keys_of(item).issubset(allowed_keys)

    # Check correct preservation of fields for the tool entry
    tool_entries = [i for i in hist if i["role"] == "tool"]
    assert len(tool_entries) == 1
    assert tool_entries[0]["tool_calls"] == [{"name": "toolX"}]

    # Check file paths passed through
    assert saved_output_file == output_file
    assert saved_traj_path == traj_path

    # Check logging call
    assert len(log_calls) == 1
    assert f"Saved demo to {output_file}" in log_calls[0]
