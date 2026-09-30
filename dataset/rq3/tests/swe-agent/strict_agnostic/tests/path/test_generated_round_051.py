import types
from types import SimpleNamespace
from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class ToolsStub:
    """A deterministic stub for the tools.parse_actions interface.

    parse_actions accepts a completion dict and returns a 2-tuple where the
    second element is the action string that contains the information checked
    by contains_edits.
    """

    def __init__(self):
        # allow customizing behavior per-instance if needed later
        pass

    def parse_actions(self, completion):
        # Accept either explicit 'action' key or 'text' key; default to empty string
        action = completion.get("action") if isinstance(completion, dict) else ""
        if not action:
            action = completion.get("text") if isinstance(completion, dict) else ""
        # Return a 2-tuple to match the unpacking in contains_edits
        return (None, action)


def make_btc_with_tools(tools):
    """Create a BinaryTrajectoryComparison instance without running its __init__
    to avoid side effects. We only need the _tools attribute for contains_edits.
    """
    btc = object.__new__(BinaryTrajectoryComparison)
    # Attach the stub tools that provides parse_actions
    btc._tools = tools
    return btc


def test_contains_edits_empty_round_051():
    """When completions is empty, contains_edits should return False."""
    tools = ToolsStub()
    btc = make_btc_with_tools(tools)

    completions = []
    assert btc.contains_edits(completions) is False


def test_contains_edits_single_edit_round_051():
    """A single completion whose parsed action starts with 'edit' yields True."""
    tools = ToolsStub()
    btc = make_btc_with_tools(tools)

    completions = [{"action": "edit replace some text"}]
    assert btc.contains_edits(completions) is True


def test_contains_edits_later_match_round_051():
    """If the first completion doesn't match but a later one does, the function
    should keep iterating and eventually return True."""
    tools = ToolsStub()
    btc = make_btc_with_tools(tools)

    completions = [
        {"action": "some other action"},
        {"action": "str_replace_editor insert into file"},
    ]
    # First item does not start with any keyword, second does -> True
    assert btc.contains_edits(completions) is True


def test_contains_edits_all_non_matching_round_051():
    """Multiple completions that do not start with any of the keywords should
    lead to a final False result."""
    tools = ToolsStub()
    btc = make_btc_with_tools(tools)

    completions = [
        {"action": "examine file"},
        {"action": "log something"},
        {"action": "modify_but_not_using_editor"},
    ]
    assert btc.contains_edits(completions) is False
