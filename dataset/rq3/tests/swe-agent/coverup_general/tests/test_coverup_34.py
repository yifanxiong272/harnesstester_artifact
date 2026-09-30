# file: sweagent/agent/history_processors.py:269-296
# asked: {"lines": [285, 286, 287, 288, 289, 291, 292, 293, 294, 295, 296], "branches": [[286, 287], [286, 296], [288, 289], [288, 291], [292, 293], [292, 295]]}
# gained: {"lines": [285, 286, 287, 288, 289, 291, 292, 293, 294, 295, 296], "branches": [[286, 287], [286, 296], [288, 289], [288, 291], [292, 293], [292, 295]]}

import copy
import pytest
from sweagent.agent.history_processors import RemoveRegex


def test_remove_regex_applies_to_string_and_list_and_preserves_original():
    # prepare history with mixed content types and a last entry that should be kept
    history = [
        {"content": "before <diff>secret1</diff> after"},
        {"content": [{"text": "list <diff>secret2</diff> end"}]},
        {"content": "last <diff>keepme</diff>"},
    ]
    original = copy.deepcopy(history)

    processor = RemoveRegex(keep_last=1)  # keep the last entry unchanged
    result = processor(history)

    # Ensure we got the same number of items and order preserved
    assert isinstance(result, list)
    assert len(result) == len(history)

    # First entry was a string and should have the diff removed
    assert isinstance(result[0]["content"], str)
    assert "<diff>" not in result[0]["content"]
    assert "secret1" not in result[0]["content"]
    # The textual content should reflect removal (ensure something was removed)
    assert result[0]["content"].strip() == "before  after".strip() or "before after" in result[0][
        "content"
    ]

    # Second entry was a list with one message and should have had its text modified
    assert isinstance(result[1]["content"], list)
    assert len(result[1]["content"]) == 1
    assert "<diff>" not in result[1]["content"][0]["text"]
    assert "secret2" not in result[1]["content"][0]["text"]

    # Third entry is within keep_last and should remain exactly as the original
    assert result[2] == original[2]

    # Original history must remain unchanged (deepcopy inside processor)
    assert history == original


def test_remove_regex_with_multiple_patterns_and_dotall_on_list_content():
    # content spans multiple lines inside the diff tag and also contains a SECRET token
    history = [
        {
            "content": [
                {
                    "text": "line SECRET <diff>multi\nline\nsecret_data</diff> done"
                }
            ]
        }
    ]
    original = copy.deepcopy(history)

    # Provide multiple patterns to remove: SECRET token and the diff block (DOTALL)
    processor = RemoveRegex(remove=["SECRET", r"<diff>.*</diff>"], keep_last=0)
    result = processor(history)

    assert len(result) == 1
    # Ensure both patterns were removed
    text = result[0]["content"][0]["text"]
    assert "SECRET" not in text
    assert "<diff>" not in text
    assert "secret_data" not in text
    # Some whitespace may remain where removals occurred; check that meaningful parts remain
    assert text.strip().startswith("line")
    assert text.strip().endswith("done")

    # Original history should remain unchanged
    assert history == original
