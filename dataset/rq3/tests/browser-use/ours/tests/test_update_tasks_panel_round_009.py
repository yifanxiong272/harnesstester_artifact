import types
import builtins
import browser_use.cli as cli


def _make_widgets():
    class FakeTasksInfo:
        def __init__(self):
            self.cleared = False
            self.writes = []

        def clear(self):
            self.cleared = True

        def write(self, s):
            # Normalize None -> '' behavior (code may write empty strings)
            self.writes.append('' if s is None else s)

    class FakeTasksPanel:
        def __init__(self):
            self.scrolled = None

        def scroll_end(self, animate=False):
            # record the animate flag
            self.scrolled = animate

    return FakeTasksInfo(), FakeTasksPanel()


def _make_agent_with_history():
    # Build objects that match the attribute access patterns used by update_tasks_panel
    class Message:
        def __init__(self, content):
            self.content = content

    class HistoryProvider:
        def __init__(self, messages):
            self._messages = messages

        def get_messages(self):
            return list(self._messages)

    class MessageManager:
        def __init__(self, messages):
            self.state = types.SimpleNamespace(history=HistoryProvider(messages))

    class CurrentState:
        def __init__(self, next_goal=None, evaluation_previous_goal=None):
            self.next_goal = next_goal
            self.evaluation_previous_goal = evaluation_previous_goal

    class ModelOutput:
        def __init__(self, current_state=None, action=None):
            self.current_state = current_state
            self.action = action

    class Result:
        def __init__(self, error=None, extracted_content=None):
            self.error = error
            self.extracted_content = extracted_content

    class ActionMock:
        def __init__(self, payload):
            self._payload = payload

        # the code calls action.model_dump(exclude_unset=True)
        def model_dump(self, exclude_unset=True):
            return dict(self._payload)

    class Item:
        def __init__(self, model_output=None, result=None):
            self.model_output = model_output
            self.result = result or []

    # Messages: one original task message to be parsed
    msg = Message('Your ultimate task is: """Do the thing"""')
    mm = MessageManager([msg])

    # Build two history items to exercise evaluation and action/result branches
    # First item: has a goal but no evaluation (idx=1)
    cs1 = CurrentState(next_goal='First goal\nmore lines', evaluation_previous_goal=None)
    mo1 = ModelOutput(current_state=cs1, action=None)
    item1 = Item(model_output=mo1, result=None)

    # Second item: has evaluation, an action, and a result with extracted_content
    cs2 = CurrentState(next_goal='Second goal', evaluation_previous_goal='Success previous step')
    action = ActionMock({'open_url': {'url': 'http://example'}})
    mo2 = ModelOutput(current_state=cs2, action=[action])
    res2 = Result(error=None, extracted_content='extracted result text')
    item2 = Item(model_output=mo2, result=[res2])

    # Agent object with the expected nested attributes
    agent = types.SimpleNamespace()
    agent._message_manager = mm
    # state.n_steps is used to determine current step number
    agent.state = types.SimpleNamespace(n_steps=2, history=True, paused=False)
    # Note: the code checks hasattr(self.agent.state, 'history') but later uses self.agent.history.history
    # so provide both .state.history and .history.history
    agent.state.history = True
    agent.history = types.SimpleNamespace(history=[item1, item2])
    # running flag to exercise the 'actively working' branch
    agent.running = True

    return agent


def test_agent_none_round_009():
    # Test when there is no agent: should write the 'Agent not initialized' dim message and scroll
    tasks_info, tasks_panel = _make_widgets()

    # Ensure module symbol RichLog exists (passed as a type to query_one in code)
    setattr(cli, 'RichLog', object)

    app = object.__new__(cli.BrowserUseApp)

    # Provide a query_one that returns the appropriate fake widget based on selector
    def query_one(selector, *args, **kwargs):
        if selector == '#tasks-info':
            return tasks_info
        elif selector == '#tasks-panel':
            return tasks_panel
        raise KeyError(selector)

    app.query_one = query_one
    # No agent attribute -> covered branch writing 'Agent not initialized'
    if hasattr(app, 'agent'):
        delattr(app, 'agent')

    # Call the method under test
    app.update_tasks_panel()

    # Assertions: tasks_info cleared and the 'Agent not initialized' message present
    assert tasks_info.cleared is True, "tasks_info.clear() should have been called"
    # Look for the dim message that should be written when agent is None
    assert any('[dim]Agent not initialized' in w for w in tasks_info.writes), tasks_info.writes
    # Ensure the panel was scrolled to bottom with animate=False
    assert tasks_panel.scrolled is False


def test_agent_with_history_round_009():
    # Test the complex branch where agent has message history, steps, actions, and results
    tasks_info, tasks_panel = _make_widgets()

    setattr(cli, 'RichLog', object)

    app = object.__new__(cli.BrowserUseApp)

    def query_one(selector, *args, **kwargs):
        if selector == '#tasks-info':
            return tasks_info
        elif selector == '#tasks-panel':
            return tasks_panel
        raise KeyError(selector)

    app.query_one = query_one

    # Attach a crafted agent with messages, history, actions, and results
    agent = _make_agent_with_history()
    app.agent = agent

    # Run the function under test
    app.update_tasks_panel()

    writes = '\n'.join(tasks_info.writes)

    # Validate that original TASK was extracted and displayed
    assert '[bold green]TASK:[/]' in writes
    assert 'Do the thing' in writes

    # Validate that STEPS header is present
    assert '[bold yellow]STEPS:[/]' in writes

    # Validate that goals are summarized (first line only)
    assert 'Goal:' in writes
    assert 'First goal' in writes or 'Second goal' in writes

    # Evaluation should be shown for the second step and map 'Success' -> checkmark char
    # The code replaces 'Success' with the check mark \u2705
    assert '\u2705' in writes or 'Evaluation' in writes

    # Actions header and action name (open_url) should be present
    assert '[purple]Actions:[/]' in writes
    assert 'open_url' in writes

    # Result content should be displayed
    assert 'Result' in writes and 'extracted result text' in writes

    # The agent was set running=True, so active working indicator should be present
    assert any('[yellow]Agent is actively working' in w for w in tasks_info.writes)

    # Ensure scroll_end was called on the panel
    assert tasks_panel.scrolled is False
