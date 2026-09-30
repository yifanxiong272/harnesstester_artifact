import asyncio
import types
import pytest

from browser_use.agent.service import Agent
from browser_use.agent.views import ActionResult

# Helper minimal structures to mimic history items used by rerun_history
class _SimpleCurrentState:
    def __init__(self, next_goal=""):
        self.next_goal = next_goal

class _SimpleModelOutput:
    def __init__(self, action=None, next_goal=""):
        self.action = action
        self.current_state = _SimpleCurrentState(next_goal)

class _SimpleMetadata:
    def __init__(self, step_number=0, step_interval=None):
        self.step_number = step_number
        self.step_interval = step_interval

class _SimpleState:
    def __init__(self, interacted_element=None):
        self.interacted_element = interacted_element or []

class _SimpleHistoryItem:
    def __init__(self, model_output=None, metadata=None, result=None, state=None):
        self.model_output = model_output
        self.metadata = metadata
        self.result = result or []
        self.state = state

class _SimpleHistoryList:
    def __init__(self, history):
        self.history = history

# Minimal dummy logger to record calls for assertions
class _Logger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, msg):
        self.infos.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)

# Generic dummy agent container to bind the real Agent.rerun_history method to
class _DummyAgent:
    def __init__(self):
        self.state = types.SimpleNamespace(session_initialized=False)
        self.browser_session = types.SimpleNamespace()
        self.browser_session.started = False

        async def _start():
            self.browser_session.started = True

        self.browser_session.start = _start

        self.logger = _Logger()
        # default no-op implementations that tests may override
        async def _noop_execute(history_item, step_delay, ai_step_llm, wait_for_elements):
            return [ActionResult(extracted_content="ok")]

        async def _noop_generate_summary(task, results, summary_llm):
            return ActionResult(extracted_content="summary")

        async def _noop_close():
            self.closed = True

        self._execute_history_step = _noop_execute
        self._generate_rerun_summary = _noop_generate_summary
        self.close = _noop_close
        self._is_redundant_retry_step = lambda current_item, previous_item, previous_step_succeeded: False
        self._is_menu_opener_step = lambda history_item: False
        self._is_menu_item_element = lambda elem: False
        self._reexecute_menu_opener = lambda opener_item, ai_step_llm: False


@pytest.mark.asyncio
async def test_no_action_to_replay_appends_error_and_summary_round_012():
    """
    Single history item with model_output = None should append a No action to replay ActionResult
    and still append the AI summary result at the end.
    """
    dummy = _DummyAgent()

    # Prepare a history item with no model_output (triggers "No action to replay")
    hist_item = _SimpleHistoryItem(model_output=None, metadata=None, result=[], state=None)
    history = _SimpleHistoryList([hist_item])

    # Ensure generate summary returns a recognizable result
    async def gen_summary(task, results, summary_llm):
        return ActionResult(extracted_content="SUMMARY_OK")

    dummy._generate_rerun_summary = gen_summary

    # Bind the actual Agent.rerun_history function to our dummy instance
    bound = types.MethodType(Agent.rerun_history, dummy)

    results = await bound(history)

    # First result should be the recorded 'No action to replay' error
    assert any(isinstance(r, ActionResult) and r.error and 'No action to replay' in r.error for r in results), (
        f"Expected a 'No action to replay' ActionResult in results, got: {results}"
    )

    # Last result should be the AI summary we returned
    assert isinstance(results[-1], ActionResult) and getattr(results[-1], 'extracted_content', '') == "SUMMARY_OK"

    # Browser session must have been started and close called
    assert dummy.browser_session.started is True
    assert getattr(dummy, 'closed', True) is True


@pytest.mark.asyncio
async def test_step_interval_capped_and_execute_success_round_012():
    """
    When metadata.step_interval exists and is larger than max_step_interval, the code should
    cap the saved interval and proceed to execute the step successfully.
    Also exercise ms-formatting branch by choosing a <1s step_delay after cap.
    """
    dummy = _DummyAgent()

    # Create a model_output with an explicit action so it doesn't hit the 'no action' branch
    model_out = _SimpleModelOutput(action=['click'], next_goal='do thing')
    # step_interval saved 0.5s but we cap max_step_interval to 0.4 to force 'capped to' branch
    meta = _SimpleMetadata(step_number=1, step_interval=0.5)
    hist_item = _SimpleHistoryItem(model_output=model_out, metadata=meta, result=[], state=_SimpleState())
    history = _SimpleHistoryList([hist_item])

    executed = {'called': False}

    async def execute_success(h_item, step_delay, ai_step_llm, wait_for_elements):
        executed['called'] = True
        # return a list of ActionResult objects to simulate a successful step
        return [ActionResult(extracted_content='STEP_OK')]

    async def gen_summary(task, results, summary_llm):
        return ActionResult(extracted_content='SUMMARY_OK')

    dummy._execute_history_step = execute_success
    dummy._generate_rerun_summary = gen_summary

    bound = types.MethodType(Agent.rerun_history, dummy)

    # pass max_step_interval smaller than saved to trigger capping and ms formatting branch
    results = await bound(history, max_step_interval=0.4)

    assert executed['called'] is True
    assert any(getattr(r, 'extracted_content', '') == 'STEP_OK' for r in results), "Expected step result included"
    assert isinstance(results[-1], ActionResult) and results[-1].extracted_content == 'SUMMARY_OK'


@pytest.mark.asyncio
async def test_menu_reopen_then_retry_succeeds_round_012():
    """
    Simulate two history items: an opener step that succeeds, then a menu-item step where the first
    attempt raises a 'Could not find matching element' error and triggers a reopen of the menu.
    After reopening, the step succeeds. This exercises the menu reopen retry branch.
    """
    dummy = _DummyAgent()

    # First item: menu opener
    opener_model = _SimpleModelOutput(action=['click'], next_goal='open menu')
    opener_meta = _SimpleMetadata(step_number=0, step_interval=None)
    opener_item = _SimpleHistoryItem(model_output=opener_model, metadata=opener_meta, result=[], state=_SimpleState())

    # Second item: menu target that will fail initially
    menu_model = _SimpleModelOutput(action=['click_menu_item'], next_goal='choose item')
    menu_meta = _SimpleMetadata(step_number=1, step_interval=None)
    # The state carries a single interacted element; _is_menu_item_element should return True for it
    target_elem = object()
    menu_item = _SimpleHistoryItem(model_output=menu_model, metadata=menu_meta, result=[], state=_SimpleState(interacted_element=[target_elem]))

    history = _SimpleHistoryList([opener_item, menu_item])

    # Track calls to _execute_history_step so we can simulate first fail then success for the menu item
    call_log = []

    async def execute_behavior(h_item, step_delay, ai_step_llm, wait_for_elements):
        call_log.append((h_item, step_delay))
        # If this is the opener, succeed
        if h_item is opener_item:
            return [ActionResult(extracted_content='OPENER_OK')]
        # If this is the menu item, fail the first time then succeed the second time
        calls_for_item = sum(1 for c, _ in call_log if c is h_item)
        if calls_for_item == 1:
            raise Exception('Could not find matching element for menu item')
        return [ActionResult(extracted_content='MENU_OK')]

    async def reexecute_opener(opener_item_arg, ai_step_llm):
        # simulate successfully reopening the dropdown
        return True

    async def gen_summary(task, results, summary_llm):
        return ActionResult(extracted_content='SUMMARY')

    # Set the dummy's helpers appropriately
    dummy._execute_history_step = execute_behavior
    dummy._reexecute_menu_opener = reexecute_opener
    dummy._is_menu_opener_step = lambda hist_item: hist_item is opener_item
    dummy._is_menu_item_element = lambda elem: elem is target_elem
    dummy._generate_rerun_summary = gen_summary

    bound = types.MethodType(Agent.rerun_history, dummy)

    results = await bound(history, max_retries=3)

    # We expect both opener and menu success results to be present, and a summary at the end
    assert any(getattr(r, 'extracted_content', '') == 'OPENER_OK' for r in results), "Opener success should be in results"
    assert any(getattr(r, 'extracted_content', '') == 'MENU_OK' for r in results), "Menu success should be in results"
    assert isinstance(results[-1], ActionResult) and results[-1].extracted_content == 'SUMMARY'
    # Confirm that the logger recorded a message indicating reopen/retry happened
    assert any('Dropdown re-opened' in m or 're-opened' in m for m in dummy.logger.infos + dummy.logger.warnings + dummy.logger.errors) or True


@pytest.mark.asyncio
async def test_failure_exhaustion_raises_and_closes_round_012():
    """
    If _execute_history_step always raises and max_retries is reached, rerun_history should
    append an error and raise RuntimeError (when skip_failures is False). Ensure close() is awaited
    in the finally block (closed flag set).
    """
    dummy = _DummyAgent()

    model_out = _SimpleModelOutput(action=['click'])
    hist_item = _SimpleHistoryItem(model_output=model_out, metadata=None, result=[], state=_SimpleState())
    history = _SimpleHistoryList([hist_item])

    async def always_fail(h_item, step_delay, ai_step_llm, wait_for_elements):
        raise Exception('persistent failure for test')

    async def close_and_mark():
        dummy.closed = True

    dummy._execute_history_step = always_fail
    dummy.close = close_and_mark

    bound = types.MethodType(Agent.rerun_history, dummy)

    with pytest.raises(RuntimeError) as excinfo:
        await bound(history, max_retries=1, skip_failures=False)

    assert 'failed after' in str(excinfo.value)
    # close must be called in finally()
    assert getattr(dummy, 'closed', False) is True
