# file: gpt_researcher/llm_provider/image/image_generator.py:268-349
# asked: {"lines": [277, 279, 280, 282, 283, 284, 285, 289, 290, 291, 292, 293, 294, 295, 296, 299, 300, 301, 303, 304, 307, 308, 309, 312, 313, 315, 321, 322, 325, 326, 328, 329, 330, 331, 332, 333, 336, 337, 340, 341, 342, 343, 345, 346, 347, 349], "branches": [[279, 280], [279, 349], [289, 290], [289, 299], [291, 292], [291, 299], [293, 294], [293, 299], [299, 279], [299, 300], [300, 301], [300, 340], [301, 300], [301, 303], [312, 313], [312, 315], [340, 300], [340, 341], [341, 340], [341, 342]]}
# gained: {"lines": [277, 279, 280, 282, 283, 284, 285, 289, 290, 291, 292, 293, 294, 295, 296, 299, 300, 301, 303, 304, 307, 308, 309, 312, 313, 315, 321, 322, 325, 326, 328, 329, 330, 331, 332, 333, 336, 337, 340, 341, 342, 343, 345, 346, 347, 349], "branches": [[279, 280], [279, 349], [289, 290], [291, 292], [293, 294], [293, 299], [299, 300], [300, 301], [300, 340], [301, 300], [301, 303], [312, 313], [312, 315], [340, 341], [341, 342]]}

import asyncio
import base64
from types import SimpleNamespace
from pathlib import Path
import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


@pytest.mark.asyncio
async def test_generate_with_gemini_base64_inline_data(tmp_path, monkeypatch):
    """
    Test that _generate_with_gemini correctly decodes base64 inline_data,
    writes the file, and returns correct metadata.
    """
    # Prepare provider and output path
    provider = ImageGeneratorProvider(model_name="models/gemini-2.5-flash-image")
    # Ensure provider has a dummy client so attribute access doesn't raise
    provider._client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda *a, **k: None))

    output_path = tmp_path / "images"
    output_path.mkdir(parents=True, exist_ok=True)

    # Create a simple PNG-like byte content and base64 encode it
    original_bytes = b"\x89PNG\r\n\x1a\nFAKEPNGDATA"
    b64_data = base64.b64encode(original_bytes).decode("ascii")

    # Build fake response structure
    part = SimpleNamespace(inline_data=SimpleNamespace(data=b64_data, mime_type="image/png"))
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]))
    response = SimpleNamespace(candidates=[candidate])

    # Monkeypatch asyncio.to_thread to return our fake response
    async def fake_to_thread(func, *args, **kwargs):
        # Ensure the passed func is the generate_content callable from our dummy client
        assert callable(func)
        return response

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    # Call the async method
    results = await provider._generate_with_gemini(
        full_prompt="full prompt",
        output_path=output_path,
        num_images=1,
        research_id="research123",
        original_prompt="a test prompt",
    )

    # Assertions on returned metadata
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    assert item["prompt"] == "a test prompt"
    assert "research123" in item["url"]
    assert Path(item["path"]).exists()
    # File content matches decoded bytes
    with open(item["path"], "rb") as f:
        data = f.read()
    assert data == original_bytes


@pytest.mark.asyncio
async def test_generate_with_gemini_multiple_branches_and_exception(tmp_path, monkeypatch):
    """
    Test multiple iterations including:
    - an iteration where asyncio.to_thread raises (caught by except)
    - an iteration where response has parts with text but no inline_data (logs warning path)
    - an iteration where inline_data is bytes (written directly)
    """
    provider = ImageGeneratorProvider(model_name="models/gemini-2.5-flash-image")
    # Provide a dummy client so attribute access to .models.generate_content doesn't raise
    provider._client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda *a, **k: None))

    output_path = tmp_path / "images2"
    output_path.mkdir(parents=True, exist_ok=True)

    # Prepare responses for three calls
    # 1) Will raise an exception
    # 2) Returns a candidate with a text part (no inline_data)
    text_part = SimpleNamespace(text="I refuse to generate an image; here's text instead.")
    candidate_text = SimpleNamespace(content=SimpleNamespace(parts=[text_part]))
    response_text = SimpleNamespace(candidates=[candidate_text])

    # 3) Returns a candidate with inline_data as bytes
    image_bytes = b"JPEGBYTESFAKE"
    part_bytes = SimpleNamespace(inline_data=SimpleNamespace(data=image_bytes, mime_type="image/jpeg"))
    candidate_bytes = SimpleNamespace(content=SimpleNamespace(parts=[part_bytes]))
    response_bytes = SimpleNamespace(candidates=[candidate_bytes])

    responses = [
        Exception("simulated failure"),
        response_text,
        response_bytes,
    ]

    async def seq_to_thread(func, *args, **kwargs):
        # Ensure callable is passed
        assert callable(func)
        if not responses:
            return response_bytes
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(asyncio, "to_thread", seq_to_thread)

    results = await provider._generate_with_gemini(
        full_prompt="full prompt 2",
        output_path=output_path,
        num_images=3,
        research_id="",  # empty research id to use alternative URL branch
        original_prompt="another prompt",
    )

    # Only one successful image should be produced (the last one)
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    # Since research_id was empty, url should not contain it (but still starts with outputs path)
    assert item["url"].startswith("/outputs/images/")
    assert item["prompt"] == "another prompt"
    # File exists and contains the exact bytes written
    path = Path(item["path"])
    assert path.exists()
    with open(path, "rb") as f:
        got = f.read()
    assert got == image_bytes
