# file: browser_use/cli.py:1375-1485
# asked: {"lines": [1375, 1377, 1378, 1380, 1382, 1383, 1386, 1387, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1398, 1399, 1400, 1402, 1403, 1404, 1407, 1410, 1411, 1412, 1414, 1415, 1417, 1419, 1422, 1423, 1426, 1427, 1430, 1433, 1435, 1436, 1438, 1439, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1451, 1452, 1453, 1454, 1455, 1457, 1458, 1459, 1460, 1463, 1464, 1465, 1466, 1467, 1468, 1469, 1470, 1473, 1476, 1477, 1478, 1479, 1481, 1484, 1485], "branches": [[1380, 1382], [1380, 1481], [1386, 1387], [1386, 1407], [1391, 1392], [1391, 1398], [1392, 1391], [1392, 1393], [1394, 1391], [1394, 1395], [1398, 1399], [1398, 1407], [1400, 1402], [1400, 1404], [1402, 1400], [1402, 1403], [1411, 1412], [1411, 1476], [1414, 1415], [1414, 1476], [1417, 1419], [1417, 1476], [1422, 1423], [1422, 1426], [1426, 1427], [1426, 1430], [1433, 1435], [1433, 1451], [1436, 1438], [1436, 1443], [1444, 1445], [1444, 1451], [1451, 1452], [1451, 1463], [1453, 1454], [1453, 1463], [1455, 1453], [1455, 1457], [1458, 1453], [1458, 1459], [1463, 1464], [1463, 1473], [1464, 1465], [1464, 1473], [1465, 1466], [1465, 1468], [1468, 1464], [1468, 1469], [1476, 1477], [1476, 1478], [1478, 1479], [1478, 1484]]}
# gained: {"lines": [1375, 1377, 1378, 1380, 1382, 1383, 1386, 1387, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1398, 1399, 1400, 1402, 1403, 1404, 1407, 1410, 1411, 1412, 1414, 1415, 1417, 1419, 1422, 1423, 1426, 1427, 1430, 1433, 1435, 1436, 1438, 1439, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1451, 1452, 1453, 1454, 1455, 1457, 1458, 1459, 1460, 1463, 1464, 1465, 1466, 1467, 1468, 1469, 1470, 1473, 1476, 1477, 1478, 1479, 1481, 1484, 1485], "branches": [[1380, 1382], [1380, 1481], [1386, 1387], [1386, 1407], [1391, 1392], [1391, 1398], [1392, 1393], [1394, 1395], [1398, 1399], [1400, 1402], [1400, 1404], [1402, 1403], [1411, 1412], [1414, 1415], [1414, 1476], [1417, 1419], [1417, 1476], [1422, 1423], [1422, 1426], [1426, 1427], [1426, 1430], [1433, 1435], [1436, 1438], [1436, 1443], [1444, 1445], [1444, 1451], [1451, 1452], [1451, 1463], [1453, 1454], [1453, 1463], [1455, 1457], [1458, 1459], [1463, 1464], [1464, 1465], [1464, 1473], [1465, 1466], [1465, 1468], [1468, 1469], [1476, 1477], [1476, 1478], [1478, 1479]]}

import pytest
from types import SimpleNamespace

from browser_use.cli import BrowserUseApp

class FakeRichLog:
    def __init__(self):
        self.cleared = False
        self.lines = []

    def clear(self):
        self.cleared = True

    def write(self, text: str):
        # collect written lines for assertions
        self.lines.append(text)

class FakePanel:
    def __init__(self):
        self.scroll_calls = []

    def scroll_end(self, animate=False):
        self.scroll_calls.append({"animate": animate})

class FakeAction:
    def __init__(self, dump):
        self._dump = dump
    def model_dump(self, exclude_unset=True):
        return self._dump

class FakeResult:
    def __init__(self, error=None, extracted_content=None):
        self.error = error
        self.extracted_content = extracted_content

class FakeCurrentState:
    def __init__(self, next_goal=None, evaluation_previous_goal=None):
        self.next_goal = next_goal
        self.evaluation_previous_goal = evaluation_previous_goal

class FakeModelOutput:
    def __init__(self, current_state=None, action=None):
        self.current_state = current_state
        self.action = action or []

class FakeHistoryItem:
    def __init__(self, model_output=None, result=None):
        self.model_output = model_output
        self.result = result or []

class FakeMessage:
    def __init__(self, content):
        self.content = content

class FakeMessageHistory:
    def __init__(self, messages):
        self._messages = messages
    def get_messages(self):
        return self._messages

class FakeMessageManagerState:
    def __init__(self, history):
        self.history = history

class FakeMessageManager:
    def __init__(self, state):
        self.state = state

class FakeAgentHistory:
    def __init__(self, history_list):
        self.history = history_list

class FakeAgentState:
    def __init__(self, n_steps=0, history=None, paused=False):
        self.n_steps = n_steps
        self.history = history
        self.paused = paused

def make_app_with_widgets():
    # BrowserUseApp requires a config argument with .get; use a plain dict.
    app = BrowserUseApp({})

    fake_log = FakeRichLog()
    fake_panel = FakePanel()

    def fake_query_one(selector, *args, **kwargs):
        if selector == "#tasks-info":
            return fake_log
        if selector == "#tasks-panel":
            return fake_panel
        raise KeyError(f"Unknown selector: {selector}")

    # Replace the instance method
    app.query_one = fake_query_one
    return app, fake_log, fake_panel

def test_update_tasks_panel_agent_not_initialized():
    app, fake_log, fake_panel = make_app_with_widgets()
    app.agent = None

    # Call the method under test
    app.update_tasks_panel()

    # Assertions: ensure the not-initialized message was written and clear was called
    assert fake_log.cleared is True
    assert any('Agent not initialized' in line for line in fake_log.lines)
    # Ensure the panel scroll_end was called with animate=False
    assert fake_panel.scroll_calls == [{"animate": False}]

def test_update_tasks_panel_agent_full_running():
    app, fake_log, fake_panel = make_app_with_widgets()

    # Create messages containing an original task
    msg = FakeMessage('Intro... Your ultimate task is: """Test Task Alpha""" Bye')
    message_history = FakeMessageHistory([msg])
    message_manager_state = FakeMessageManagerState(message_history)
    message_manager = FakeMessageManager(message_manager_state)

    # History items:
    # Item 1: has a goal and an action and a successful extracted_content result
    cs1 = FakeCurrentState(next_goal="First goal line\nmore details", evaluation_previous_goal=None)
    action1 = FakeAction({"open_url": "http://example.com"})
    mo1 = FakeModelOutput(current_state=cs1, action=[action1])
    res1 = FakeResult(error=None, extracted_content="Found something important")
    item1 = FakeHistoryItem(model_output=mo1, result=[res1])

    # Item 2: current step, has an evaluation_previous_goal and an error
    cs2 = FakeCurrentState(next_goal=None, evaluation_previous_goal="Success: Completed task")
    mo2 = FakeModelOutput(current_state=cs2, action=[])
    res2 = FakeResult(error="Something went wrong", extracted_content=None)
    item2 = FakeHistoryItem(model_output=mo2, result=[res2])

    history_list = [item1, item2]
    agent_history = FakeAgentHistory(history_list)

    # Agent with state.n_steps == 2 to make second step be current
    agent_state = FakeAgentState(n_steps=2, history=True, paused=False)

    agent = SimpleNamespace()
    agent._message_manager = message_manager
    agent.state = agent_state
    agent.history = agent_history
    agent.running = True

    app.agent = agent

    # Execute
    app.update_tasks_panel()

    # Assertions for content
    # Task extracted
    assert any("TASK" in line for line in fake_log.lines)
    assert any("Test Task Alpha" in line for line in fake_log.lines)

    # Steps header
    assert any("STEPS" in line for line in fake_log.lines)

    # Goal summary from first item
    assert any("Goal" in line and "First goal line" in line for line in fake_log.lines)

    # Evaluation summary for second item should be replaced 'Success' -> '✅'
    assert any("Evaluation" in line and ("✅" in line or "❌" in line) for line in fake_log.lines)

    # Actions list should include the action name open_url
    assert any("Actions" in line for line in fake_log.lines)
    assert any("open_url" in line for line in fake_log.lines)

    # Result from first item and Error from second
    assert any("Result" in line and "Found something important" in line for line in fake_log.lines)
    assert any("Error" in line and "Something went wrong" in line for line in fake_log.lines)

    # Agent running indicator
    assert any("actively working" in line for line in fake_log.lines)

    # Ensure scroll_end called
    assert fake_panel.scroll_calls == [{"animate": False}]

def test_update_tasks_panel_agent_paused_shows_paused_message():
    app, fake_log, fake_panel = make_app_with_widgets()

    # No messages, no history to keep things minimal
    agent_state = FakeAgentState(n_steps=0, history=True, paused=True)

    # agent.history.history empty so steps won't be printed
    agent_history = FakeAgentHistory([])

    agent = SimpleNamespace()
    agent._message_manager = None
    agent.state = agent_state
    agent.history = agent_history
    agent.running = False

    app.agent = agent

    app.update_tasks_panel()

    # Should have paused message
    assert any("Agent is paused" in line for line in fake_log.lines)
    assert fake_panel.scroll_calls == [{"animate": False}]
