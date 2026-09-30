from openhands.agenthub.codeact_agent.action_parser import CodeActActionParserAgentDelegate


class DummyMatch:
    def __init__(self, g0: str, g1: str):
        self._g0 = g0
        self._g1 = g1

    def group(self, i: int) -> str:
        if i == 0:
            return self._g0
        if i == 1:
            return self._g1
        raise IndexError("only groups 0 and 1 are supported in this test mock")


def test_probe_001():
    """
    Probe for duplicate terminal punctuation when the thought already ends with a period.

    Constructs a parser instance, sets a deterministic agent_delegate mock, and ensures
    parse(...) does not produce two consecutive periods at the boundary where a '.' is
    unconditionally appended by the implementation.
    """
    # Thought intentionally ends with a period to trigger the potential duplication
    thought = "I think."
    delegate_token = "[delegate]"
    browse_actions = "open the browser"

    # action_str contains the delegate token so replacement yields the thought (with trailing '.')
    action_str = f"{thought} {delegate_token}"

    # Create instance without calling __init__ to avoid constructor requirements
    inst = object.__new__(CodeActActionParserAgentDelegate)
    inst.agent_delegate = DummyMatch(delegate_token, browse_actions)

    result = inst.parse(action_str)

    # Validate structure of returned action and the primary invariant
    assert hasattr(result, "inputs"), "parse must return an object with an 'inputs' attribute"
    task = result.inputs.get("task") if isinstance(result.inputs, dict) else None
    assert isinstance(task, str), f"expected task string in returned Action inputs, got: {type(task)!r}"

    # Primary oracle: no duplicated terminal period introduced by concatenation
    assert ".." not in task, f"duplicate terminal punctuation detected in task: {task!r}"
