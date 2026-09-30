# file: gpt_researcher/agent.py:450-491
# asked: {"lines": [469, 471, 472, 473, 474, 475, 479, 480, 481, 482, 483, 484, 487, 488, 489, 491], "branches": []}
# gained: {"lines": [469, 471, 472, 473, 474, 475, 479, 480, 481, 482, 483, 484, 487, 488, 489, 491], "branches": []}

import types
import sys
from pathlib import Path
import importlib
import pytest


def import_gpt_researcher_module():
    """
    Locate the repository's top-level directory that contains the outer 'gpt_researcher'
    package and import either 'gpt_researcher.gpt_researcher.agent' or
    'gpt_researcher.agent' depending on layout.
    """
    cwd = Path(__file__).resolve().parent
    # Search upwards for a parent that contains a 'gpt_researcher' directory
    for p in [cwd] + list(cwd.parents):
        outer = p / "gpt_researcher"
        if not outer.exists():
            continue
        # Case A: nested package gpt_researcher/gpt_researcher/agent.py
        nested_agent = outer / "gpt_researcher" / "agent.py"
        flat_agent = outer / "agent.py"
        try:
            sys.path.insert(0, str(p))
            if nested_agent.exists():
                return importlib.import_module("gpt_researcher.gpt_researcher.agent")
            if flat_agent.exists():
                return importlib.import_module("gpt_researcher.agent")
        except Exception:
            # On failure try next candidate
            continue
        finally:
            # Clean up sys.path insertion if it is still present and not needed
            if sys.path and sys.path[0] == str(p):
                sys.path.pop(0)
    raise RuntimeError("Could not locate gpt_researcher.agent module")


@pytest.mark.asyncio
async def test_write_report_with_no_images():
    mod = import_gpt_researcher_module()
    GPTResearcher = getattr(mod, "GPTResearcher")

    # Create instance without invoking full __init__
    researcher = object.__new__(GPTResearcher)

    # Set up attributes expected by write_report
    researcher.available_images = []  # no images
    researcher._current_step = "initial"
    researcher.context = ["internal context"]
    log_calls = []

    async def fake_log_event(event_type, **kwargs):
        log_calls.append((event_type, kwargs))

    researcher._log_event = fake_log_event

    # fake report generator
    rg_calls = []

    async def fake_write_report(*, existing_headers, relevant_written_contents, ext_context, custom_prompt, available_images):
        rg_calls.append({
            "existing_headers": existing_headers,
            "relevant_written_contents": relevant_written_contents,
            "ext_context": ext_context,
            "custom_prompt": custom_prompt,
            "available_images": available_images,
        })
        return "generated-report-no-images"

    researcher.report_generator = types.SimpleNamespace(write_report=fake_write_report)

    # Execute
    result = await researcher.write_report(
        existing_headers=["h1"],
        relevant_written_contents=["prev"],
        ext_context=None,
        custom_prompt="prompt",
    )

    # Assertions
    assert result == "generated-report-no-images"
    assert researcher._current_step == "report_writing"

    assert len(rg_calls) == 1
    call = rg_calls[0]
    assert call["existing_headers"] == ["h1"]
    assert call["relevant_written_contents"] == ["prev"]
    # ext_context should default to researcher.context
    assert call["ext_context"] == researcher.context
    assert call["custom_prompt"] == "prompt"
    assert call["available_images"] == []

    # _log_event called twice
    assert len(log_calls) == 2
    first_event_type, first_kwargs = log_calls[0]
    assert first_event_type == "research"
    assert first_kwargs.get("step") == "writing_report"
    details = first_kwargs.get("details", {})
    assert details["existing_headers"] == ["h1"]
    assert details["context_source"] == "internal"
    assert details["available_images_count"] == 0

    second_event_type, second_kwargs = log_calls[1]
    assert second_event_type == "research"
    assert second_kwargs.get("step") == "report_completed"
    details2 = second_kwargs.get("details", {})
    assert details2["report_length"] == len("generated-report-no-images")
    assert details2["images_embedded"] == 0


@pytest.mark.asyncio
async def test_write_report_with_images_and_external_context():
    mod = import_gpt_researcher_module()
    GPTResearcher = getattr(mod, "GPTResearcher")

    # Create instance without invoking full __init__
    researcher = object.__new__(GPTResearcher)

    # Set up attributes expected by write_report
    researcher.available_images = [{"id": "img1"}, {"id": "img2"}]
    researcher._current_step = "something-else"
    researcher.context = ["internal context should be ignored"]
    log_calls = []

    async def fake_log_event(event_type, **kwargs):
        log_calls.append((event_type, kwargs))

    researcher._log_event = fake_log_event

    rg_calls = []

    async def fake_write_report(*, existing_headers, relevant_written_contents, ext_context, custom_prompt, available_images):
        rg_calls.append({
            "existing_headers": existing_headers,
            "relevant_written_contents": relevant_written_contents,
            "ext_context": ext_context,
            "custom_prompt": custom_prompt,
            "available_images": available_images,
        })
        return f"report-with-{len(available_images)}-images"

    researcher.report_generator = types.SimpleNamespace(write_report=fake_write_report)

    ext_ctx = ["external context"]

    result = await researcher.write_report(
        existing_headers=[],
        relevant_written_contents=[],
        ext_context=ext_ctx,
        custom_prompt="custom",
    )

    assert result == "report-with-2-images"
    assert researcher._current_step == "report_writing"

    assert len(rg_calls) == 1
    call = rg_calls[0]
    # available_images should be exactly the attribute list
    assert call["available_images"] is researcher.available_images
    assert call["ext_context"] == ext_ctx
    assert call["custom_prompt"] == "custom"

    assert len(log_calls) == 2
    _, first_kwargs = log_calls[0]
    details = first_kwargs.get("details", {})
    assert details["available_images_count"] == 2
    assert details["context_source"] == "external"

    _, second_kwargs = log_calls[1]
    details2 = second_kwargs.get("details", {})
    assert details2["report_length"] == len("report-with-2-images")
    assert details2["images_embedded"] == 2
