import asyncio
from types import SimpleNamespace
import pytest

from multi_agents.agents.reviewer import ReviewerAgent


def make_agent_with_attrs(websocket=None, stream_output=None):
    # Bypass __init__ to avoid depending on unknown constructor behavior
    ag = object.__new__(ReviewerAgent)
    # assign attributes the implementation expects
    ag.websocket = websocket
    ag.stream_output = stream_output
    return ag


async def _run_review(agent, draft_state, call_model_return, trackers):
    """
    Helper to patch call_model and print_agent_output deterministically.
    trackers is a dict used to return captured values to the test.
    """
    # Patch the model call and print utilities on the module where review_draft resolves them
    import multi_agents.agents.reviewer as reviewer_mod

    async def fake_call_model(prompt, model=None):
        # record the two arguments for assertions
        trackers['call_model_prompt'] = prompt
        trackers['call_model_model'] = model
        return call_model_return

    def fake_print_agent_output(msg, agent=None):
        trackers.setdefault('print_calls', []).append((msg, agent))

    async def fake_stream_output(stream_type, event, message, websocket):
        trackers.setdefault('stream_calls', []).append((stream_type, event, message, websocket))

    # apply patches
    reviewer_mod.call_model = fake_call_model
    reviewer_mod.print_agent_output = fake_print_agent_output

    # attach stream_output to agent if the test provided one
    if agent.stream_output is None:
        # ensure attribute exists for code path where it's checked
        agent.stream_output = None

    # invoke the async method under test
    result = await agent.review_draft(draft_state)
    return result


@pytest.mark.asyncio
async def test_review_draft_returns_none_and_streams_round_069():
    """
    - Simulate a draft_state where revision_notes exist and task.verbose is True.
    - Provide a websocket and async stream_output on the agent so the branch that awaits
      stream_output is executed.
    - The mocked call_model returns a string containing the substring "None" so the
      function should return None.
    - Assert that call_model was called with a prompt containing the guidelines, draft,
      and the revision prompt, and that stream_output was awaited with the expected
      formatted message.
    """
    trackers = {}

    # make a sample draft_state with guidelines and revision_notes
    draft_state = {
        "task": {
            "guidelines": ["Be concise", "Cite sources"],
            "model": "test-model",
            "verbose": True,
        },
        "revision_notes": "Previous reviewer fixed grammar.",
        "draft": "This is a draft that mostly follows guidelines.",
    }

    # create agent with a websocket and stream_output that will capture the call
    async def fake_stream_output(stream_type, event, message, websocket):
        trackers.setdefault('stream_calls', []).append((stream_type, event, message, websocket))

    agent = make_agent_with_attrs(websocket=SimpleNamespace(id="ws-1"), stream_output=fake_stream_output)

    # run review_draft where the model returns a response containing the substring 'None'
    returned = await _run_review(agent, draft_state, call_model_return="Everything looks fine. None", trackers=trackers)

    # Assertions about return value
    assert returned is None

    # Assertions about call_model invocation
    assert 'call_model_prompt' in trackers
    prompt = trackers['call_model_prompt']
    # prompt must be a list of two role dicts per implementation
    assert isinstance(prompt, list) and len(prompt) == 2
    # the user content should include Guidelines and Draft text
    user_content = prompt[1]['content']
    assert 'Guidelines:' in user_content
    assert 'Draft:' in user_content
    assert 'Be concise' in user_content
    assert draft_state['draft'] in user_content
    # since revision_notes was provided, the revise prompt text should be included
    assert 'Previous reviewer fixed grammar.' in user_content

    # Ensure stream_output was awaited with the expected formatted message
    assert 'stream_calls' in trackers
    stream_call = trackers['stream_calls'][-1]
    # (stream_type, event, message, websocket)
    assert stream_call[0] == 'logs'
    assert stream_call[1] == 'review_feedback'
    # message contains the response plus the trailing ellipsis used by the implementation
    assert 'Everything looks fine. None...' in stream_call[2]
    # websocket object passed through
    assert hasattr(stream_call[3], 'id') and stream_call[3].id == 'ws-1'


@pytest.mark.asyncio
async def test_review_draft_prints_when_no_websocket_round_069():
    """
    - Simulate a draft_state where there are no revision_notes and task.verbose is True,
      but the agent has no websocket (or stream_output), so the print_agent_output path
      should be executed.
    - The mocked call_model returns a response without the substring "None" so the
      function should return the raw response string.
    - Assert that print_agent_output was invoked with the expected formatted message,
      and that the function returns the exact response.
    """
    trackers = {}

    draft_state = {
        "task": {
            "guidelines": ["Be accurate"],
            "model": "test-model-2",
            "verbose": True,
        },
        # no revision_notes provided -> revise_prompt should be omitted
        "revision_notes": "",
        "draft": "An inaccurate draft.",
    }

    # Create agent with no websocket and no stream_output to force print_agent_output path
    agent = make_agent_with_attrs(websocket=None, stream_output=None)

    # Run where call_model returns a non-None-containing response
    response_text = "Please revise section 2: accuracy issues"
    returned = await _run_review(agent, draft_state, call_model_return=response_text, trackers=trackers)

    # Assertions about return value
    assert returned == response_text

    # Ensure print_agent_output was called once with the expected message
    assert 'print_calls' in trackers and len(trackers['print_calls']) == 1
    printed_msg, printed_agent = trackers['print_calls'][0]
    assert 'Review feedback is: ' in printed_msg
    # trailing ellipsis used by implementation
    assert response_text + '...' in printed_msg
    # agent label expected to be 'REVIEWER' per implementation call signature
    assert printed_agent == 'REVIEWER'

    # Ensure the prompt sent to call_model includes the guidelines and draft but not revision notes
    prompt = trackers['call_model_prompt']
    user_content = prompt[1]['content']
    assert 'Be accurate' in user_content
    assert 'An inaccurate draft.' in user_content
    # revision_notes was empty so the revise prompt fragment should not appear
    assert 'Previous reviewer' not in user_content
