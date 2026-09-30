import types
from browser_use.cli import BrowserUseApp


class MockPanel:
    def __init__(self):
        self.writes = []
        self.cleared = False
        self.scroll_calls = []

    def clear(self):
        self.cleared = True
        self.writes.append(('clear', None))

    def write(self, msg=''):
        # Normalize None -> empty string to match calls that use write('')
        self.writes.append(('write', '' if msg is None else msg))

    def scroll_end(self, animate=False):
        self.scroll_calls.append({'animate': animate})


class ActionMock:
    def model_dump(self, exclude_unset=True):
        # Return a mapping so the code can pick the action name
        return {"open_url": {}}


class MessageMock:
    def __init__(self, content):
        self.content = content


class MsgHistoryMock:
    def __init__(self, messages):
        self._messages = messages

    def get_messages(self):
        return self._messages


def make_fake_self():
    """Create a minimal fake `self` object suitable for calling
    BrowserUseApp.update_tasks_panel without initializing the full app.
    """
    fake = types.SimpleNamespace()

    tasks_info = MockPanel()
    tasks_panel = MockPanel()

    def query_one(selector, cls=None):
        if selector == '#tasks-info':
            return tasks_info
        if selector == '#tasks-panel':
            return tasks_panel
        raise KeyError(selector)

    fake.query_one = query_one
    fake._mock_tasks_info = tasks_info
    fake._mock_tasks_panel = tasks_panel

    return fake


def test_update_tasks_panel_agent_none_round_010():
    """When self.agent is falsy, the 'Agent not initialized' message is shown
    and the tasks panel is scrolled to the end (animate=False).
    """
    fake = make_fake_self()
    # No agent attribute (or None) should trigger the fallback branch
    fake.agent = None

    # Call the class method with our fake instance
    BrowserUseApp.update_tasks_panel(fake)

    # Inspect recorded writes
    writes = [w for t, w in fake._mock_tasks_info.writes if t == 'write']

    # Expect the specific dimmed 'Agent not initialized' text
    assert any('[dim]Agent not initialized' in w for w in writes), writes

    # Ensure scroll_end was called exactly once and animate was False
    assert fake._mock_tasks_panel.scroll_calls, "scroll_end was not called"
    assert fake._mock_tasks_panel.scroll_calls[-1] == {'animate': False}


def test_update_tasks_panel_with_history_and_running_round_010():
    """Exercise the branch where an agent exists with message history,
    tasks are extracted from message content, history items are shown
    (including goal, evaluation, actions, results and errors), and the
    running indicator is displayed.
    """
    fake = make_fake_self()

    # Construct a fake agent with nested attributes used by the function
    agent = types.SimpleNamespace()

    # Message manager: provide a message containing the triple-quote task
    msg = MessageMock('Your ultimate task is: """Important Task"""')
    msg_hist = MsgHistoryMock([msg])
    agent._message_manager = types.SimpleNamespace(state=types.SimpleNamespace(history=msg_hist))

    # State: indicate number of steps and provide a .history marker (truthy)
    agent.state = types.SimpleNamespace(n_steps=2, history=True, paused=False)

    # Also provide agent.history.history (note: source checks state.history but then uses agent.history)
    # Prepare two history items to exercise idx==current_step and idx>1 evaluation
    # Item 1: has a result with extracted_content and a goal and an action
    item1_result = types.SimpleNamespace(error=None, extracted_content='FirstResult')
    item1_model_output = types.SimpleNamespace(
        current_state=types.SimpleNamespace(next_goal='Do thing A\nDetails', evaluation_previous_goal=''),
        action=[ActionMock()],
    )
    item1 = types.SimpleNamespace(result=[item1_result], model_output=item1_model_output)

    # Item 2: has an error, goal, and an evaluation text that will be transformed
    item2_result = types.SimpleNamespace(error='Something failed', extracted_content=None)
    item2_model_output = types.SimpleNamespace(
        current_state=types.SimpleNamespace(next_goal='Do thing B', evaluation_previous_goal='Success previous step'),
        action=[],
    )
    item2 = types.SimpleNamespace(result=[item2_result], model_output=item2_model_output)

    agent.history = types.SimpleNamespace(history=[item1, item2])

    # Set running True to hit the 'Agent is actively working' branch
    agent.running = True

    fake.agent = agent

    BrowserUseApp.update_tasks_panel(fake)

    writes = [w for t, w in fake._mock_tasks_info.writes if t == 'write']

    # Check that the TASK header and the extracted task text are present
    assert any('[bold green]TASK' in w for w in writes), writes
    assert any('Important Task' in w for w in writes), writes

    # Check STEPS header and step lines for both steps (Step 1/2 and Step 2/2)
    assert any('STEPS' in w for w in writes), writes
    assert any('Step 1/2' in w for w in writes), writes
    assert any('Step 2/2' in w for w in writes), writes

    # Goal summary from first item should be shown (first line only)
    assert any('Goal:' in w and 'Do thing A' in w for w in writes), writes

    # Evaluation for the second item should be transformed (contains check mark replacement for 'Success')
    # The code replaces 'Success' with a checkmark prefix; ensure Evaluation text appears
    assert any('Evaluation' in w for w in writes), writes

    # Actions: the action name from ActionMock.model_dump appears
    assert any('Actions' in w for w in writes), writes
    assert any('open_url' in w for w in writes), writes

    # Result and Error outputs expected for items
    assert any('Result' in w and 'FirstResult' in w for w in writes), writes
    assert any('Error' in w and 'Something failed' in w for w in writes), writes

    # Running indicator shown
    assert any('Agent is actively working' in w for w in writes), writes

    # Ensure scroll_end called
    assert fake._mock_tasks_panel.scroll_calls and fake._mock_tasks_panel.scroll_calls[-1] == {'animate': False}


def test_update_tasks_panel_agent_paused_round_010():
    """If the agent is not running but its state.paused is True, the paused
    message should be displayed instead of the running indicator.
    """
    fake = make_fake_self()

    agent = types.SimpleNamespace()
    agent._message_manager = None
    agent.state = types.SimpleNamespace(n_steps=0, history=True, paused=True)
    # Provide agent.history.history as empty to avoid writing steps
    agent.history = types.SimpleNamespace(history=[])
    agent.running = False

    fake.agent = agent

    BrowserUseApp.update_tasks_panel(fake)

    writes = [w for t, w in fake._mock_tasks_info.writes if t == 'write']

    # Should not show the running indicator, but should show the paused message
    assert any('Agent is paused' in w or 'paused' in w for w in writes), writes
    assert not any('Agent is actively working' in w for w in writes)

    # Ensure scroll_end called
    assert fake._mock_tasks_panel.scroll_calls and fake._mock_tasks_panel.scroll_calls[-1] == {'animate': False}
