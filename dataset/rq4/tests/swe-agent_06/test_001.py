def test_probe_001():
    # Purpose: exercise BinaryTrajectoryComparison.contains_edits when parse_actions
    # yields an action string with leading whitespace. The public invariant:
    #   if the parsed action string (after incidental whitespace) begins with
    #   an edit keyword, contains_edits should return True.
    from sweagent.agent.action_sampler import BinaryTrajectoryComparison

    class DummyTools:
        """Deterministic mock of the ToolHandler.parse_actions interface.
        Always returns a (thought, action) tuple where action begins with
        incidental leading whitespace followed by the edit keyword.
        """

        def parse_actions(self, completion):
            # leading whitespace before the edit keyword is the boundary condition
            return ("some thought", "  edit change the text")

    # Instantiate with minimal deterministic args (constructor does not require
    # the actual types at runtime for this probe). Override _tools to control parsing.
    sampler = BinaryTrajectoryComparison(config=None, model=None, tools=None)
    sampler._tools = DummyTools()

    completions = [{"any": "value"}]

    # Primary behavioral oracle: contains_edits SHOULD recognize the edit even
    # though the action string has leading whitespace and return True.
    assert sampler.contains_edits(completions) is True
