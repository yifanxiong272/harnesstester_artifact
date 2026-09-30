import asyncio
from types import SimpleNamespace

import gpt_researcher.skills.writer as writer_module
from gpt_researcher.skills.writer import ReportGenerator


def _make_researcher(*, verbose, query="Q", context=None, cfg_agent_role=None, role="fallback", websocket=None, extra_kwargs=None):
    cfg = SimpleNamespace(agent_role=cfg_agent_role)
    # a simple cost callback sentinel
    def add_costs(amount):
        # deterministic side-effect: record into closure
        recorded.append(('cost', amount))
    recorded = []
    researcher = SimpleNamespace(
        verbose=verbose,
        query=query,
        context=context or "CTX",
        cfg=cfg,
        role=role,
        websocket=websocket or object(),
        add_costs=add_costs,
        prompt_family="pf",
        kwargs=extra_kwargs or {},
    )
    return researcher, recorded


def test_verbose_true_round_143():
    # Setup researcher with verbose True and cfg.agent_role set
    researcher, recorded = _make_researcher(verbose=True, query="my query", cfg_agent_role="agentX", extra_kwargs={'foo': 'bar'})

    # Prepare spies to capture calls
    stream_calls = []
    async def fake_stream_output(stream, event, message, websocket):
        # record call details deterministically
        stream_calls.append((stream, event, message, websocket))
        return None

    intro_calls = []
    async def fake_write_report_introduction(query, context, agent_role_prompt, config, websocket, cost_callback, prompt_family, **kwargs):
        # record incoming parameters so we can assert them
        intro_calls.append({
            'query': query,
            'context': context,
            'agent_role_prompt': agent_role_prompt,
            'config': config,
            'websocket': websocket,
            'cost_callback': cost_callback,
            'prompt_family': prompt_family,
            'kwargs': kwargs,
        })
        # call the cost_callback deterministically to show it can be invoked
        cost_callback(1.23)
        return {'introduction': f'intro for {query}'}

    # Patch the module-level symbols where ReportGenerator resolves them
    writer_module.stream_output = fake_stream_output
    writer_module.write_report_introduction = fake_write_report_introduction

    # Construct ReportGenerator without calling its real __init__ to avoid external dependencies
    rg = object.__new__(ReportGenerator)
    rg.researcher = researcher

    # Execute the async method synchronously in the test
    result = asyncio.run(rg.write_introduction())

    # Assertions: returned value equals the stubbed introduction
    assert result == {'introduction': 'intro for my query'}

    # stream_output should have been called twice (before and after introduction)
    assert len(stream_calls) == 2
    # first call should be the "writing_introduction" event and include the query in the message
    assert stream_calls[0][1] == 'writing_introduction'
    assert "my query" in stream_calls[0][2]
    # second call should be the "introduction_written" event
    assert stream_calls[1][1] == 'introduction_written'

    # write_report_introduction should have been called exactly once with expected agent_role_prompt
    assert len(intro_calls) == 1
    call = intro_calls[0]
    assert call['query'] == 'my query'
    assert call['agent_role_prompt'] == 'agentX'
    # the kwargs passed-through should include our extra foo key
    assert call['kwargs'].get('foo') == 'bar'

    # ensure the cost callback the writer passed was our add_costs function (and it got called)
    assert recorded == [('cost', 1.23)]


def test_verbose_false_round_143():
    # Setup researcher with verbose False and cfg.agent_role None so role is used
    researcher, recorded = _make_researcher(verbose=False, query="another", cfg_agent_role=None, role='the_role', extra_kwargs={'x': 1})

    stream_calls = []
    async def fake_stream_output(stream, event, message, websocket):
        stream_calls.append((stream, event, message, websocket))
        return None

    intro_calls = []
    async def fake_write_report_introduction(query, context, agent_role_prompt, config, websocket, cost_callback, prompt_family, **kwargs):
        intro_calls.append({
            'query': query,
            'agent_role_prompt': agent_role_prompt,
            'kwargs': kwargs,
        })
        return 'plain intro'

    # Patch module-level symbols again for this test
    writer_module.stream_output = fake_stream_output
    writer_module.write_report_introduction = fake_write_report_introduction

    rg = object.__new__(ReportGenerator)
    rg.researcher = researcher

    result = asyncio.run(rg.write_introduction())

    # When verbose is False, stream_output should not be called
    assert stream_calls == []

    # write_report_introduction should be called and return the value we provided
    assert result == 'plain intro'
    assert len(intro_calls) == 1
    call = intro_calls[0]
    # Because cfg.agent_role is falsy, agent_role_prompt should fall back to researcher.role
    assert call['agent_role_prompt'] == 'the_role'
    # kwargs were forwarded
    assert call['kwargs'].get('x') == 1
