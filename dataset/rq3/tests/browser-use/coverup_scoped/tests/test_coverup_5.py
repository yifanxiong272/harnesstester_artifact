# file: browser_use/agent/service.py:3092-3271
# asked: {"lines": [3124, 3127, 3129, 3132, 3133, 3135, 3136, 3137, 3138, 3139, 3142, 3144, 3146, 3147, 3149, 3150, 3151, 3153, 3155, 3156, 3157, 3159, 3160, 3162, 3165, 3166, 3167, 3169, 3170, 3171, 3174, 3175, 3176, 3177, 3178, 3180, 3181, 3182, 3185, 3190, 3191, 3192, 3193, 3194, 3195, 3199, 3201, 3202, 3203, 3205, 3206, 3207, 3208, 3209, 3210, 3211, 3212, 3214, 3215, 3216, 3221, 3222, 3223, 3224, 3227, 3228, 3229, 3230, 3231, 3233, 3234, 3235, 3238, 3239, 3240, 3241, 3243, 3244, 3245, 3247, 3248, 3249, 3253, 3254, 3255, 3257, 3260, 3261, 3264, 3265, 3266, 3268, 3271], "branches": [[3136, 3137], [3136, 3264], [3142, 3144], [3142, 3155], [3146, 3147], [3146, 3149], [3150, 3151], [3150, 3153], [3156, 3157], [3156, 3159], [3164, 3169], [3164, 3174], [3175, 3176], [3175, 3190], [3190, 3191], [3190, 3201], [3207, 3208], [3207, 3260], [3220, 3227], [3220, 3243], [3229, 3230], [3229, 3243], [3234, 3235], [3234, 3243], [3243, 3244], [3243, 3253], [3248, 3207], [3248, 3249]]}
# gained: {"lines": [3124, 3127, 3129, 3132, 3133, 3135, 3136, 3137, 3138, 3139, 3142, 3144, 3146, 3147, 3149, 3150, 3151, 3153, 3155, 3156, 3157, 3160, 3162, 3165, 3166, 3167, 3169, 3170, 3171, 3174, 3175, 3176, 3177, 3178, 3180, 3181, 3182, 3185, 3190, 3191, 3192, 3193, 3194, 3195, 3199, 3201, 3202, 3203, 3205, 3206, 3207, 3208, 3209, 3210, 3211, 3212, 3214, 3215, 3216, 3221, 3222, 3223, 3224, 3227, 3228, 3229, 3230, 3231, 3233, 3234, 3235, 3238, 3239, 3240, 3241, 3243, 3244, 3245, 3247, 3248, 3249, 3253, 3254, 3255, 3257, 3260, 3261, 3264, 3265, 3266, 3268, 3271], "branches": [[3136, 3137], [3136, 3264], [3142, 3144], [3142, 3155], [3146, 3147], [3146, 3149], [3150, 3151], [3150, 3153], [3156, 3157], [3164, 3169], [3164, 3174], [3175, 3176], [3175, 3190], [3190, 3191], [3190, 3201], [3207, 3208], [3220, 3227], [3220, 3243], [3229, 3230], [3234, 3235], [3243, 3244], [3243, 3253], [3248, 3249]]}

import asyncio
import types
import pytest

from browser_use.agent.service import Agent
from browser_use.agent.views import ActionResult


class _S:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


async def _noop_async(*a, **k):
    return None


@pytest.mark.asyncio
async def test_rerun_history_various_branches_and_summary(monkeypatch):
    # Create an Agent instance without calling __init__
    agent = object.__new__(Agent)

    # State and flags
    agent.state = _S(session_initialized=False)
    started = {"called": False}
    closed = {"called": False}

    async def fake_start():
        started["called"] = True

    async def fake_close():
        closed["called"] = True

    agent.browser_session = _S(start=fake_start)
    agent.close = fake_close

    # Simple logger that records messages
    logs = {"info": [], "warning": [], "error": []}

    class Logger:
        def info(self, *a, **k):
            logs["info"].append(" ".join(map(str, a)))

        def warning(self, *a, **k):
            logs["warning"].append(" ".join(map(str, a)))

        def error(self, *a, **k):
            logs["error"].append(" ".join(map(str, a)))

    # Replace class-level logger property/descriptor with our logger instance for this test
    monkeypatch.setattr(Agent, "logger", Logger(), raising=False)

    # Will be used to generate summary at the end
    summary_action = ActionResult(extracted_content="RERUN SUMMARY")

    async def fake_generate_rerun_summary(task, results, summary_llm):
        # Verify it receives the aggregated results
        assert isinstance(results, list)
        # return a recognizable summary ActionResult
        return summary_action

    agent._generate_rerun_summary = fake_generate_rerun_summary

    # Control execute behavior: return success for items that have tag 'succeed'
    async def fake_execute_history_step(history_item, step_delay, ai_step_llm, wait_for_elements):
        # simulate check on a marker on history_item
        if getattr(history_item, "should_raise", False):
            raise RuntimeError("unexpected execution error")
        # produce an ActionResult unique per history item
        tag = getattr(history_item, "tag", "ok")
        return [ActionResult(extracted_content=f"executed-{tag}")]

    agent._execute_history_step = fake_execute_history_step

    # Redundant retry detection: return True if item has redundant=True
    def fake_is_redundant_retry_step(history_item, previous_item, previous_step_succeeded):
        return getattr(history_item, "redundant", False)

    agent._is_redundant_retry_step = fake_is_redundant_retry_step

    # Menu related stubs (not used in this test)
    agent._is_menu_opener_step = lambda prev: False
    agent._is_menu_item_element = lambda elem: False
    agent._reexecute_menu_opener = lambda prev, ai_step_llm: False

    # Avoid actual sleeping delays
    async def fake_sleep(duration):
        # record that we would have slept for >0 durations in logs
        logs["info"].append(f"sleep({duration})")

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # Build history items to hit multiple branches:
    # 1) item_no_action -> model_output is None -> No action to replay
    item_no_action = _S(model_output=None, metadata=None, result=[], state=None, tag="no_action")

    # 2) item_ms_delay -> metadata.step_interval small (<1.0), model_output with action and next_goal
    model_out_small = _S(current_state=_S(next_goal="goal small"), action=["click"])
    meta_small = _S(step_interval=0.2, step_number=0)
    item_ms_delay = _S(model_output=model_out_small, metadata=meta_small, result=[], state=None, tag="small")

    # 3) item_skip_original_error -> had original error and skip_failures True
    model_out_err = _S(current_state=_S(next_goal="err goal"), action=["click"])
    meta_err = _S(step_interval=50.0, step_number=2)  # will be capped branch (> max_step_interval)
    # original result contains an object with .error property
    class ErrObj:
        def __init__(self, error):
            self.error = error

    item_skip_original_error = _S(model_output=model_out_err, metadata=meta_err, result=[ErrObj("original failure")], state=None, tag="err")

    # 4) item_redundant -> model_output present but redundant True -> should be skipped via redundant detection
    model_out_red = _S(current_state=_S(next_goal="redundant"), action=["click"])
    meta_red = _S(step_interval=None, step_number=3)
    item_redundant = _S(model_output=model_out_red, metadata=meta_red, result=[], state=None, redundant=True, tag="redundant")

    history_list = _S(history=[item_no_action, item_ms_delay, item_skip_original_error, item_redundant])

    # Attach a dummy task attribute used by _generate_rerun_summary
    agent.task = _S(id="task-1")

    # Call rerun_history with skip_failures True to hit skipping branch
    results = await agent.rerun_history(history_list, max_retries=2, skip_failures=True, delay_between_actions=0.6, max_step_interval=45.0, summary_llm=None, ai_step_llm=None, wait_for_elements=False)

    # Validate that browser_session.start was called and session flag was set
    assert agent.state.session_initialized is True
    assert started["called"] is True

    # Expected results:
    # item_no_action -> ActionResult(error='No action to replay')
    # item_ms_delay -> executed-small (from _execute_history_step)
    # item_skip_original_error -> Skipped (since skip_failures True)
    # item_redundant -> Skipped - redundant retry (extracted_content)
    # plus final summary_action appended
    texts = [getattr(r, "error", None) or getattr(r, "extracted_content", None) for r in results]
    assert any(x == "No action to replay" for x in texts)
    assert any("executed-small" in (x or "") for x in texts)
    assert any((x or "").startswith("Skipped - original step had error") for x in texts)
    assert any((x or "") == "Skipped - redundant retry of previous step" or (x or "").startswith("Skipped - redundant retry") for x in texts)
    # final element should be the summary_action we returned
    assert results[-1] is summary_action

    # Ensure close was called in finally
    assert closed["called"] is True


@pytest.mark.asyncio
async def test_rerun_history_menu_reopen_and_retry_and_failure(monkeypatch):
    # Test the menu reopen flow where an element match failure triggers re-open of menu,
    # and also the scenario where retries are exhausted and RuntimeError is raised.
    agent = object.__new__(Agent)
    agent.state = _S(session_initialized=False)

    started = {"called": False}
    closed = {"called": False}

    async def fake_start():
        started["called"] = True

    async def fake_close():
        closed["called"] = True

    agent.browser_session = _S(start=fake_start)
    agent.close = fake_close

    # Replace class-level logger with a no-op logger for this test
    monkeypatch.setattr(Agent, "logger", types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None, error=lambda *a, **k: None), raising=False)

    # We'll record reexecute calls
    reexecute_called = {"count": 0}

    async def fake_reexecute_menu_opener(previous_item, ai_step_llm):
        reexecute_called["count"] += 1
        return True

    agent._reexecute_menu_opener = fake_reexecute_menu_opener

    # Menu opener detection: previous item flagged
    def fake_is_menu_opener_step(prev):
        return getattr(prev, "is_menu_opener", False)

    agent._is_menu_opener_step = fake_is_menu_opener_step

    # Menu item detection: element with attribute is_menu_item True
    def fake_is_menu_item_element(elem):
        return getattr(elem, "is_menu_item", False)

    agent._is_menu_item_element = fake_is_menu_item_element

    # For this test, make _execute_history_step raise on the first call for the target item,
    # then succeed on subsequent call.
    call_counts = {"calls": 0}

    async def fake_execute(history_item, step_delay, ai_step_llm, wait_for_elements):
        # If this is the flaky item, raise first time
        if getattr(history_item, "tag", "") == "flaky":
            call_counts["calls"] += 1
            if call_counts["calls"] == 1:
                raise RuntimeError("Could not find matching element for selector")
            return [ActionResult(extracted_content="flaky-success")]
        # For other items, just succeed
        return [ActionResult(extracted_content=f"ok-{getattr(history_item, 'tag', 'x')}")]

    agent._execute_history_step = fake_execute

    # Redundant check always false here
    agent._is_redundant_retry_step = lambda a, b, c: False

    # Sleep no-op
    async def fake_sleep(d):
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # _generate_rerun_summary returns summary ActionResult
    async def fake_generate(task, results, summary_llm):
        return ActionResult(extracted_content="menu-summary")

    agent._generate_rerun_summary = fake_generate

    # Build history: first item is menu opener, second is the flaky menu item
    opener = _S(model_output=_S(current_state=_S(next_goal="open menu"), action=["click"]), metadata=_S(step_interval=None, step_number=1), result=[], state=None, is_menu_opener=True, tag="opener")
    # Flaky has state.interacted_element list with an element flagged as menu item
    elem = _S(is_menu_item=True)
    flaky_state = _S(interacted_element=[elem])
    flaky = _S(model_output=_S(current_state=_S(next_goal="choose item"), action=["click"]), metadata=_S(step_interval=None, step_number=2), result=[], state=flaky_state, tag="flaky")

    history_list = _S(history=[opener, flaky])
    agent.task = _S(id="task-2")

    # Call rerun_history with default max_retries so the reopen branch is used and success follows
    results = await agent.rerun_history(history_list, max_retries=3, skip_failures=False, delay_between_actions=0.5, ai_step_llm=None)
    # Ensure reexecute_menu_opener was called once
    assert reexecute_called["count"] == 1
    # Ensure flaky eventual success present
    assert any((getattr(r, "extracted_content", "") == "flaky-success") for r in results)
    # Ensure summary appended and last entry is the summary
    assert getattr(results[-1], "extracted_content", "") == "menu-summary"
    # Ensure close called
    assert closed["called"] is True

    # Now test retries exhausted raising RuntimeError and that close is still called
    agent2 = object.__new__(Agent)
    agent2.state = _S(session_initialized=False)
    agent2.browser_session = _S(start=fake_start)
    close2 = {"called": False}

    async def fake_close2():
        close2["called"] = True

    agent2.close = fake_close2
    # Use same no-op logger replacement at class level (already set for this test)
    # _execute_history_step always raises
    async def always_fail(*a, **k):
        raise RuntimeError("permanent failure")

    agent2._execute_history_step = always_fail
    agent2._is_redundant_retry_step = lambda a, b, c: False
    agent2._is_menu_opener_step = lambda p: False
    agent2._is_menu_item_element = lambda e: False
    agent2._reexecute_menu_opener = lambda p, l: False
    agent2._generate_rerun_summary = fake_generate
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    agent2.task = _S(id="task-3")

    bad_item = _S(model_output=_S(current_state=_S(next_goal="bad"), action=["click"]), metadata=_S(step_interval=None, step_number=1), result=[], state=None, tag="bad")
    history_bad = _S(history=[bad_item])

    with pytest.raises(RuntimeError):
        await agent2.rerun_history(history_bad, max_retries=2, skip_failures=False, delay_between_actions=0.1)

    # close should have been called from the finally clause even on exception
    assert close2["called"] is True
