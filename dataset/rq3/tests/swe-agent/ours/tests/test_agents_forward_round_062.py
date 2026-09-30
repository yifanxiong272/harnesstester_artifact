import types
import copy
import pytest
import sweagent.agent.agents as agents

# A minimal StepOutput replacement to make the forward logic deterministic and inspectable.
class SimpleStepOutput:
    def __init__(self):
        self.query = None
        self.extra_info = {}
        self.output = ""
        self.thought = ""
        self.action = ""
        self.tool_call_ids = None
        self.tool_calls = None


def test_forward_raises_total_execution_time_exceeded_round_062():
    """Trigger the early total-execution-time check and ensure the proper exception is raised.

    This covers the branch at 977->978 where DefaultAgent.forward should raise
    _TotalExecutionTimeExceeded when _total_execution_time is larger than the
    configured total_execution_timeout.
    """
    # Build a minimal fake agent instance with only the attributes the forward
    # method will access before the raise.
    fake_agent = types.SimpleNamespace()
    fake_agent._total_execution_time = 9999

    # tools.config.total_execution_timeout must be smaller to trigger the raise
    fake_agent.tools = types.SimpleNamespace(config=types.SimpleNamespace(total_execution_timeout=1))

    # Call the unbound forward function with our fake agent as self
    with pytest.raises(agents._TotalExecutionTimeExceeded):
        # history value is irrelevant for this branch
        agents.DefaultAgent.forward(fake_agent, history=[])


def test_forward_uses_action_sampler_and_populates_step_round_062():
    """Cover the _action_sampler branch and assert StepOutput populated correctly.

    This exercises the branch where self._action_sampler is not None (990->991)
    and verifies the calls to get_action, update of extra_info, parsing of actions,
    and population of tool_call_ids/tool_calls (lines 991, 992, 997, 999).
    """
    # Monkeypatch the StepOutput used inside the module so the test can observe
    # attributes easily and deterministically.
    module = agents
    orig_StepOutput = module.StepOutput
    module.StepOutput = SimpleStepOutput

    try:
        history = [{"role": "user", "content": "hello"}]

        # Construct fake agent with required attributes used by forward
        fake_agent = types.SimpleNamespace()
        fake_agent._total_execution_time = 0
        fake_agent.name = "test-agent"

        # tools with config and parse_actions method
        class Tools:
            def __init__(self):
                self.config = types.SimpleNamespace(total_execution_timeout=1000)

            def parse_actions(self, output):
                # Return a thought and an action string (action later .strip()ed)
                return ("THOUGHT_EXTRACTED", " do-something ")

        fake_agent.tools = Tools()

        # Hook that records model queries and generated actions
        class Hook:
            def __init__(self):
                self.queries = []
                self.generated = []

            def on_model_query(self, messages, agent):
                self.queries.append((messages, agent))

            def on_actions_generated(self, step):
                self.generated.append(step)

        fake_agent._chook = Hook()

        # ActionSampler.get_action must return an object with completion and extra_info
        class Best:
            def __init__(self):
                # completion is the output object expected by the code
                self.completion = {"message": "model generated message", "tool_calls": [{"id": "tool-1"}]}
                self.extra_info = {"sampled": True}

        class ActionSampler:
            def get_action(self, problem_statement, trajectory, history):
                # ensure the sampler receives the provided arguments
                assert problem_statement == "problem-xyz"
                assert isinstance(trajectory, list)
                assert history is history_arg
                return Best()

        # Provide the problem statement (assert in code must pass)
        fake_agent._problem_statement = "problem-xyz"
        fake_agent._action_sampler = ActionSampler()

        # Provide trajectory and a sentinel history object reference for assertions
        fake_agent.trajectory = []
        # keep a variable so the ActionSampler assert can reference same object
        history_arg = history

        # model is not used in this branch but set for completeness
        fake_agent.model = types.SimpleNamespace()

        # Simple logger that does nothing (avoid noisy output)
        fake_agent.logger = types.SimpleNamespace(info=lambda *a, **k: None)

        # handle_action should receive the populated step; capture it and return a value
        captured = {}

        def handle_action(step):
            captured['step'] = step
            return "handled-result"

        fake_agent.handle_action = handle_action

        # Execute forward and assert the returned result
        result = agents.DefaultAgent.forward(fake_agent, history)
        assert result == "handled-result"

        # Inspect the captured step to ensure fields were populated as expected
        step = captured.get('step')
        assert step is not None
        # query should be a deep copy of history
        assert step.query == history
        # output comes from Best.completion["message"]
        assert step.output == "model generated message"
        # thought/action populated from parse_actions
        assert step.thought == "THOUGHT_EXTRACTED"
        assert step.action.strip() == "do-something"
        # tool call ids and tool_calls set from completion
        assert step.tool_call_ids == ["tool-1"]
        assert step.tool_calls == [{"id": "tool-1"}]
        # extra_info updated from Best.extra_info
        assert step.extra_info.get("sampled") is True

        # Ensure hooks were invoked
        assert fake_agent._chook.queries, "on_model_query not called"
        assert fake_agent._chook.generated, "on_actions_generated not called"

    finally:
        # Restore original StepOutput to avoid interfering with other tests
        module.StepOutput = orig_StepOutput
