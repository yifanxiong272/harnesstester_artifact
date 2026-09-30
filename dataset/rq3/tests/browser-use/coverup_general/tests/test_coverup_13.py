# file: browser_use/cli.py:1375-1485
# asked: {"lines": [1375, 1377, 1378, 1380, 1382, 1383, 1386, 1387, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1398, 1399, 1400, 1402, 1403, 1404, 1407, 1410, 1411, 1412, 1414, 1415, 1417, 1419, 1422, 1423, 1426, 1427, 1430, 1433, 1435, 1436, 1438, 1439, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1451, 1452, 1453, 1454, 1455, 1457, 1458, 1459, 1460, 1463, 1464, 1465, 1466, 1467, 1468, 1469, 1470, 1473, 1476, 1477, 1478, 1479, 1481, 1484, 1485], "branches": [[1380, 1382], [1380, 1481], [1386, 1387], [1386, 1407], [1391, 1392], [1391, 1398], [1392, 1391], [1392, 1393], [1394, 1391], [1394, 1395], [1398, 1399], [1398, 1407], [1400, 1402], [1400, 1404], [1402, 1400], [1402, 1403], [1411, 1412], [1411, 1476], [1414, 1415], [1414, 1476], [1417, 1419], [1417, 1476], [1422, 1423], [1422, 1426], [1426, 1427], [1426, 1430], [1433, 1435], [1433, 1451], [1436, 1438], [1436, 1443], [1444, 1445], [1444, 1451], [1451, 1452], [1451, 1463], [1453, 1454], [1453, 1463], [1455, 1453], [1455, 1457], [1458, 1453], [1458, 1459], [1463, 1464], [1463, 1473], [1464, 1465], [1464, 1473], [1465, 1466], [1465, 1468], [1468, 1464], [1468, 1469], [1476, 1477], [1476, 1478], [1478, 1479], [1478, 1484]]}
# gained: {"lines": [1375, 1377, 1378, 1380, 1382, 1383, 1386, 1387, 1390, 1391, 1392, 1393, 1394, 1395, 1396, 1398, 1399, 1400, 1402, 1403, 1404, 1407, 1410, 1411, 1412, 1414, 1415, 1417, 1419, 1422, 1423, 1426, 1427, 1430, 1433, 1435, 1436, 1438, 1439, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1451, 1452, 1453, 1454, 1455, 1457, 1458, 1459, 1460, 1463, 1464, 1465, 1466, 1467, 1468, 1469, 1470, 1473, 1476, 1477, 1478, 1479, 1481, 1484, 1485], "branches": [[1380, 1382], [1380, 1481], [1386, 1387], [1391, 1392], [1391, 1398], [1392, 1393], [1394, 1395], [1398, 1399], [1400, 1402], [1400, 1404], [1402, 1403], [1411, 1412], [1414, 1415], [1417, 1419], [1417, 1476], [1422, 1423], [1422, 1426], [1426, 1427], [1426, 1430], [1433, 1435], [1436, 1438], [1444, 1445], [1444, 1451], [1451, 1452], [1453, 1454], [1453, 1463], [1455, 1457], [1458, 1459], [1463, 1464], [1464, 1465], [1464, 1473], [1465, 1466], [1465, 1468], [1468, 1469], [1476, 1477], [1476, 1478], [1478, 1479]]}

import types
import pytest

from browser_use.cli import BrowserUseApp


class FakeRichLog:
    def __init__(self):
        self.writes = []

    def clear(self):
        self.writes.append("<CLEARED>")

    def write(self, text: str):
        # store the raw text written for assertions
        self.writes.append(text)


class FakePanel:
    def __init__(self):
        self.scrolled = False
        self.animate_arg = None

    def scroll_end(self, animate: bool = True):
        self.scrolled = True
        self.animate_arg = animate


class FakeMessageHistory:
    def __init__(self, messages):
        self._messages = messages

    def get_messages(self):
        return self._messages


class FakeMessageManager:
    def __init__(self, messages):
        self.state = types.SimpleNamespace(history=FakeMessageHistory(messages))


class FakeMessage:
    def __init__(self, content):
        self.content = content


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


class FakeAction:
    def __init__(self, dump_dict):
        self._dump = dump_dict

    def model_dump(self, exclude_unset=True):
        return self._dump


class FakeHistoryHolder:
    def __init__(self, history_items):
        self.history = history_items


class FakeHistoryItem:
    def __init__(self, model_output=None, result=None):
        self.model_output = model_output
        self.result = result or []


def make_app_without_init():
    # Create instance without calling textual.App.__init__ to avoid side effects
    app = BrowserUseApp.__new__(BrowserUseApp)
    # minimal attributes used by update_tasks_panel
    app.config = {}
    app.browser_session = None
    app.controller = None
    app.agent = None
    app.llm = None
    app.task_history = []
    app.history_index = 0
    app._telemetry = None
    app._event_bus_handler_id = None
    app._event_bus_handler_func = None
    app._info_panel_timer = None
    return app


def setup_query_one(app, tasks_info_widget, panel_widget):
    def query_one(selector, *args, **kwargs):
        if selector == "#tasks-info":
            return tasks_info_widget
        if selector == "#tasks-panel":
            return panel_widget
        raise KeyError(f"Unexpected selector: {selector}")

    app.query_one = query_one


def test_update_tasks_panel_agent_not_initialized():
    app = make_app_without_init()
    # ensure agent is None
    app.agent = None
    tasks_info = FakeRichLog()
    panel = FakePanel()
    setup_query_one(app, tasks_info, panel)

    # Call the method under test
    BrowserUseApp.update_tasks_panel(app)

    # Assertions: clear should be called and message about not initialized present
    assert tasks_info.writes[0] == "<CLEARED>"
    # Last write should mention agent not initialized
    assert any("Agent not initialized" in w for w in tasks_info.writes)
    # Panel must have been scrolled to end with animate=False
    assert panel.scrolled is True
    assert panel.animate_arg is False


def test_update_tasks_panel_with_agent_history_and_messages_running_and_paused():
    # Build messages that include an original task in the expected format
    msg_content = 'Some header\nYour ultimate task is: """Do important work""" \nfooter'
    message = FakeMessage(msg_content)
    message_manager = FakeMessageManager([message])

    # Build history items: first has an error, second has a successful extracted result and evaluation
    # First item (idx=1): next_goal present, evaluation_previous_goal present but should not be shown (idx==1)
    cs1 = FakeCurrentState(next_goal="First goal\nmore detail", evaluation_previous_goal="Failed prior")
    action1 = FakeAction({"open_url": {"url": "http://example.com"}})
    mo1 = FakeModelOutput(current_state=cs1, action=[action1])
    res1 = [FakeResult(error="Something went wrong")]
    item1 = FakeHistoryItem(model_output=mo1, result=res1)

    # Second item (idx=2): next_goal present, evaluation_previous_goal present and should be shown with replacement
    cs2 = FakeCurrentState(next_goal="Second goal", evaluation_previous_goal="Success previous step")
    action2 = FakeAction({"click": {"selector": "#btn"}})
    mo2 = FakeModelOutput(current_state=cs2, action=[action2])
    res2 = [FakeResult(extracted_content="Outcome content")]
    item2 = FakeHistoryItem(model_output=mo2, result=res2)

    history_items = [item1, item2]

    # Create fake agent with required attributes
    agent = types.SimpleNamespace()
    agent._message_manager = message_manager
    # agent.state with n_steps and paused and history attribute check
    agent.state = types.SimpleNamespace(n_steps=2, paused=False, history=True)
    # agent.history.history used by code
    agent.history = FakeHistoryHolder(history_items)
    # Running True branch
    agent.running = True

    app = make_app_without_init()
    app.agent = agent

    tasks_info = FakeRichLog()
    panel = FakePanel()
    setup_query_one(app, tasks_info, panel)

    # Call update to exercise running True branch and all internals
    BrowserUseApp.update_tasks_panel(app)

    # Assertions: clear called
    assert tasks_info.writes[0] == "<CLEARED>"
    writes = "\n".join(tasks_info.writes)

    # TASK extracted and shown
    assert "TASK:" in writes
    assert "Do important work" in writes

    # STEPS header shown
    assert "STEPS:" in writes

    # Goal summaries present (only first line)
    assert "Goal:" in writes
    assert "First goal" in writes
    assert "Second goal" in writes

    # Evaluation for second step should be shown and 'Success' replaced with the checkmark
    assert "Evaluation:" in writes
    assert "✅" in writes or "❌" in writes

    # Actions names should be shown (open_url and click)
    assert "open_url" in writes
    assert "click" in writes

    # Error and Result texts displayed
    assert "Error:" in writes
    assert "Result:" in writes
    assert "Something went wrong" in writes
    assert "Outcome content" in writes

    # Running indicator should be present
    assert "Agent is actively working" in writes

    # Panel scrolled
    assert panel.scrolled is True
    assert panel.animate_arg is False

    # Now test paused branch: set running False and paused True and call again
    agent.running = False
    agent.state.paused = True

    tasks_info2 = FakeRichLog()
    panel2 = FakePanel()
    setup_query_one(app, tasks_info2, panel2)

    BrowserUseApp.update_tasks_panel(app)

    writes2 = "\n".join(tasks_info2.writes)
    assert "Agent is paused" in writes2
    assert panel2.scrolled is True
    assert panel2.animate_arg is False
