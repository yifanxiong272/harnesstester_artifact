from openhands.agenthub.codeact_agent.action_parser import CodeActActionParserAgentDelegate


def test_probe_001():
    # A minimal match-like object that satisfies the activation conditions:
    # group(0) -> a non-empty substring present in action_str
    # group(1) -> empty string
    class DummyMatch:
        def __init__(self, full, g1):
            self._full = full
            self._g1 = g1

        def group(self, idx):
            if idx == 0:
                return self._full
            if idx == 1:
                return self._g1
            raise IndexError("Only groups 0 and 1 are supported by DummyMatch")

    # Prepare deterministic inputs
    delegate_span = "<execute_browse></execute_browse>"
    match = DummyMatch(delegate_span, "")

    parser = CodeActActionParserAgentDelegate()
    # Activate the parser with our controlled match-like object
    parser.agent_delegate = match

    # action_str contains other textual content (the 'thought') and the matched span
    action_str = "Please collect the data " + delegate_span + " now"

    action = parser.parse(action_str)
    task = action.inputs['task']

    # Primary behavioral oracle: task must not end with extraneous whitespace.
    # This asserts the independent invariant that user-visible task strings should not have a trailing space.
    assert task == task.rstrip(), f"task has trailing whitespace: {repr(task)}"
