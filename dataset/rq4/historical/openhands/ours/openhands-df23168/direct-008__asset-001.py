def test_probe_001():
    # Import only the declared entrypoint class and call its parse implementation
    from openhands.agenthub.codeact_agent.action_parser import CodeActActionParserAgentDelegate

    # Minimal match-like object satisfying activation conditions:
    # - group(0) corresponds to an in-string substring (mid-string) surrounded by spaces
    # - group(1) (browse_actions) is present and non-empty
    class FakeMatch:
        def __init__(self, g0, g1):
            self._g0 = g0
            self._g1 = g1
        def group(self, i):
            if i == 0:
                return self._g0
            if i == 1:
                return self._g1
            raise IndexError("unexpected group index")

    # Create a simple container to act as `self` when calling the unbound method.
    class DummySelf:
        pass

    dummy = DummySelf()
    # group(0) is the exact substring present in action_str and surrounded by spaces
    dummy.agent_delegate = FakeMatch("[DELEGATE]", "browse actions")

    # Construct action_str so that removing '[DELEGATE]' would leave two spaces between words
    action_str = "Start [DELEGATE] end"

    # Call the class-defined parse function directly with our dummy self to exercise the target unit
    result = CodeActActionParserAgentDelegate.parse(dummy, action_str)

    # Basic sanity checks on the returned structure and extraction of the thought portion
    assert hasattr(result, "inputs"), "returned Action has no 'inputs' attribute"
    assert isinstance(result.inputs, dict), "result.inputs is not a dict"
    assert "task" in result.inputs, "result.inputs missing 'task' key"

    task = result.inputs['task']
    # The parser constructs: '{thought}. I should start with: {browse_actions}'
    thought_part = task.split('. I should start with:')[0]

    # Primary oracle: ensure no double internal spaces were introduced by removal
    assert '  ' not in thought_part, f"Detected duplicated internal spaces in thought: {thought_part!r}"
