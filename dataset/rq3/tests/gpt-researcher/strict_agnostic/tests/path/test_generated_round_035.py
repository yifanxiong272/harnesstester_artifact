import asyncio
from types import SimpleNamespace
import pytest

import importlib
writer = importlib.import_module('gpt_researcher.skills.writer')
ReportGenerator = writer.ReportGenerator

@pytest.mark.asyncio
async def test_write_report_with_images_and_verbose_round_035(monkeypatch):
    """
    Exercise branches where research_images exists, available_images provided, verbose=True,
    and report_type == 'subtopic_report'. Assert stream_output was called for images and logs,
    and generate_report received expected report_params including agent_role_prompt assignment
    and subtopic-specific keys.
    """
    calls = []

    async def fake_stream_output(kind, name, payload, websocket, flag_or_none=None, extra=None):
        # record the call in a deterministic way
        calls.append((kind, name, payload, bool(flag_or_none), extra))

    captured_generate = {}

    async def fake_generate_report(**kwargs):
        # capture the full kwargs dict for assertions
        captured_generate.update(kwargs)
        return 'REPORT-A'

    monkeypatch.setattr(writer, 'stream_output', fake_stream_output)
    monkeypatch.setattr(writer, 'generate_report', fake_generate_report)

    # Build a minimal fake researcher
    researcher = SimpleNamespace()
    researcher.get_research_images = lambda: ['sel1', 'sel2']
    researcher.websocket = 'ws'  # passed through to stream_output but ignored by fake
    researcher.verbose = True
    researcher.query = 'Test Query'
    researcher.cfg = SimpleNamespace(agent_role='AgentRoleCfg')
    researcher.role = 'FallbackRole'
    researcher.report_type = 'subtopic_report'
    researcher.parent_query = 'ParentTopic'
    researcher.add_costs = lambda *a, **k: None
    researcher.kwargs = {'kw': 'v'}
    researcher.context = 'ResearcherContext'

    # Create ReportGenerator without invoking real __init__ (avoid external behavior)
    rg = ReportGenerator.__new__(ReportGenerator)
    rg.researcher = researcher

    # Start with a research_params that has empty agent_role_prompt to trigger assignment
    rg.research_params = {
        'agent_role_prompt': '',
        # may contain other keys used by generate_report; they will be set/copied in method
    }

    # Call the async method under test
    report = await rg.write_report(
        existing_headers=['H1'],
        relevant_written_contents=['C1'],
        ext_context=None,
        custom_prompt='Custom!',
        available_images=['pre1']
    )

    # Oracles / assertions
    assert report == 'REPORT-A'

    # stream_output should have been called for images selection and logs (images_available, writing_report, report_written)
    # We expect at least one 'images' call and logs calls when verbose=True
    kinds = [c[0] for c in calls]
    names = [c[1] for c in calls]
    assert 'images' in kinds
    assert ('images_available' in names) or ('writing_report' in names) or ('report_written' in names)

    # generate_report should have been called and received updated params
    # agent_role_prompt should have been filled from cfg.agent_role
    assert captured_generate.get('agent_role_prompt') == 'AgentRoleCfg'

    # Context should be researcher.context when ext_context is None
    assert captured_generate.get('context') == 'ResearcherContext'

    # Subtopic-specific keys should be present for subtopic_report branch
    assert captured_generate.get('main_topic') == 'ParentTopic'
    assert captured_generate.get('existing_headers') == ['H1']
    assert captured_generate.get('relevant_written_contents') == ['C1']
    # cost_callback should be passed
    assert callable(captured_generate.get('cost_callback'))


@pytest.mark.asyncio
async def test_write_report_without_images_and_nonverbose_round_035(monkeypatch):
    """
    Exercise branches where no research_images, available_images is None (defaulting to []),
    verbose=False, and report_type != 'subtopic_report'. Assert stream_output not called,
    and generate_report received available_images as empty list and cost_callback in else branch.
    """
    calls = []

    async def fake_stream_output(kind, name, payload, websocket, flag_or_none=None, extra=None):
        calls.append((kind, name, payload, flag_or_none, extra))

    captured_generate = {}

    async def fake_generate_report(**kwargs):
        captured_generate.update(kwargs)
        return 'REPORT-B'

    monkeypatch.setattr(writer, 'stream_output', fake_stream_output)
    monkeypatch.setattr(writer, 'generate_report', fake_generate_report)

    researcher = SimpleNamespace()
    researcher.get_research_images = lambda: []  # no research images
    researcher.websocket = None
    researcher.verbose = False
    researcher.query = 'NoImagesQuery'
    researcher.cfg = SimpleNamespace(agent_role=None)
    researcher.role = 'RoleX'
    researcher.report_type = 'full_report'  # not subtopic_report
    researcher.parent_query = None
    researcher.add_costs = lambda *a, **k: 'costs-called'
    researcher.kwargs = {}
    researcher.context = 'Ctx'

    rg = ReportGenerator.__new__(ReportGenerator)
    rg.researcher = researcher

    # Provide a research_params with a non-empty agent_role_prompt so branch that sets it is skipped
    rg.research_params = {
        'agent_role_prompt': 'PreSetPrompt'
    }

    # Call with available_images=None to hit the defaulting logic at the top of the method
    report = await rg.write_report(existing_headers=[], relevant_written_contents=[], ext_context='ExtCtx', custom_prompt='', available_images=None)

    assert report == 'REPORT-B'

    # Because verbose=False, fake_stream_output should not have been awaited, so calls should be empty
    assert calls == []

    # generate_report should have been called and should see available_images as [] (default)
    assert isinstance(captured_generate, dict)
    assert captured_generate.get('available_images') == []

    # Since report_type != 'subtopic_report', cost_callback should be present in params (else branch)
    assert callable(captured_generate.get('cost_callback'))
