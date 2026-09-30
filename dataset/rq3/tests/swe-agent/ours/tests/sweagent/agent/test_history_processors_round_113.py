import pytest

from sweagent.agent.history_processors import TagToolCallObservations


def test_no_tool_calls_results_in_no_added_tags_round_113():
    """If an action entry has an empty tool_calls list, tags should not be added.

    This exercises the branch where `if not function_calls: return False` (line 167->168).
    """
    processor = TagToolCallObservations(function_names={"irrelevant"})

    history = [
        {
            "message_type": "action",
            "tool_calls": [],
            "tags": ["existing"],
        }
    ]

    returned = processor(history)

    # The same history object should be returned (identity not strictly required,
    # but content must be unchanged because tool_calls was empty).
    assert returned is history

    # tags should remain unchanged because there were no tool_calls
    assert history[0]["tags"] == ["existing"]


def test_adds_keep_output_tag_when_function_name_matches_round_113():
    """When a tool call lists a function whose name intersects processor.function_names,
    the configured tags should be added to the entry.
    """
    processor = TagToolCallObservations(function_names={"do_stuff"})

    history = [
        {
            "message_type": "action",
            # tool_calls structure must include function -> name as the implementation expects
            "tool_calls": [
                {"function": {"name": "do_stuff"}, "args": []}
            ],
            # start with no tags to ensure processor adds its default tag
            "tags": [],
        }
    ]

    returned = processor(history)

    assert returned is history

    # Tag order is not guaranteed because implementation uses a set then list;
    # assert based on set semantics.
    assert set(history[0]["tags"]) == {"keep_output"}


def test_non_action_message_type_no_tagging_round_113():
    """Entries that are not of message_type 'action' must not be altered."""
    processor = TagToolCallObservations(function_names={"do_stuff"})

    history = [
        {
            "message_type": "observation",
            "tool_calls": [
                {"function": {"name": "do_stuff"}}
            ],
            "tags": [],
        }
    ]

    returned = processor(history)

    assert returned is history
    # No tagging should occur for non-action message types
    assert history[0]["tags"] == []
