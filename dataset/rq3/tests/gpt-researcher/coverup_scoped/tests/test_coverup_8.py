# file: gpt_researcher/llm_provider/image/image_generator.py:268-349
# asked: {"lines": [277, 279, 280, 282, 283, 284, 285, 289, 290, 291, 292, 293, 294, 295, 296, 299, 300, 301, 303, 304, 307, 308, 309, 312, 313, 315, 321, 322, 325, 326, 328, 329, 330, 331, 332, 333, 336, 337, 340, 341, 342, 343, 345, 346, 347, 349], "branches": [[279, 280], [279, 349], [289, 290], [289, 299], [291, 292], [291, 299], [293, 294], [293, 299], [299, 279], [299, 300], [300, 301], [300, 340], [301, 300], [301, 303], [312, 313], [312, 315], [340, 300], [340, 341], [341, 340], [341, 342]]}
# gained: {"lines": [277, 279, 280, 282, 283, 284, 285, 289, 290, 291, 292, 293, 294, 295, 296, 299, 300, 301, 303, 304, 307, 308, 309, 312, 313, 315, 321, 322, 325, 326, 328, 329, 330, 331, 332, 333, 336, 337, 340, 341, 342, 343, 345, 346, 347, 349], "branches": [[279, 280], [279, 349], [289, 290], [291, 292], [293, 294], [293, 299], [299, 300], [300, 301], [300, 340], [301, 300], [301, 303], [312, 313], [312, 315], [340, 341], [341, 342]]}

import asyncio
import base64
from pathlib import Path
import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


class _InlineData:
    def __init__(self, data, mime_type=None):
        self.data = data
        self.mime_type = mime_type or "image/png"


class _Part:
    def __init__(self, inline_data=None, text=None):
        self.inline_data = inline_data
        self.text = text


class _Content:
    def __init__(self, parts):
        self.parts = parts


class _Candidate:
    def __init__(self, content):
        self.content = content


class _Response:
    def __init__(self, candidates):
        self.candidates = candidates


class _Models:
    def __init__(self, func):
        # func should be a callable that accepts model and contents kwargs
        self.generate_content = func


class _Client:
    def __init__(self, func):
        self.models = _Models(func)


@pytest.mark.asyncio
async def test_generate_with_gemini_base64_inline(tmp_path, monkeypatch):
    """
    Test branch where part.inline_data.data is a base64-encoded string and mime_type contains 'png'.
    Ensures file is written, return structure includes research_id in url, and image bytes match decoded content.
    """
    provider = ImageGeneratorProvider()
    # monkeypatch filename/alt_text generation to deterministic names
    monkeypatch.setattr(provider, "_generate_image_filename", lambda prompt, index: f"test_png_{index}.png")
    monkeypatch.setattr(provider, "_generate_alt_text", lambda prompt: f"alt_{prompt}")

    # Prepare a base64-encoded image payload
    raw = b"PNGDATABYTES"
    b64 = base64.b64encode(raw).decode("ascii")
    inline = _InlineData(data=b64, mime_type="image/png")
    part = _Part(inline_data=inline)
    content = _Content(parts=[part])
    candidate = _Candidate(content=content)
    response = _Response(candidates=[candidate])

    # generator function to be used by to_thread
    def gen_func(model=None, contents=None):
        # assert that model and contents are passed through
        assert model == provider.model_name
        assert isinstance(contents, str)
        return response

    provider._client = _Client(gen_func)

    output_path = tmp_path
    result = await provider._generate_with_gemini(
        full_prompt="full prompt",
        output_path=output_path,
        num_images=1,
        research_id="research123",
        original_prompt="orig prompt",
    )

    # Assertions
    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    # file should exist and contain decoded bytes
    expected_file = output_path / "test_png_0.png"
    assert expected_file.exists()
    with open(expected_file, "rb") as f:
        content_bytes = f.read()
    assert content_bytes == raw
    # check returned dict fields
    assert "path" in item and item["path"] == str(expected_file.resolve())
    assert "absolute_url" in item and item["absolute_url"] == str(expected_file.resolve())
    assert item["url"].endswith("/outputs/images/research123/test_png_0.png")
    assert item["prompt"] == "orig prompt"
    assert item["alt_text"] == "alt_orig prompt"


@pytest.mark.asyncio
async def test_generate_with_gemini_bytes_inline_and_no_researchid(tmp_path, monkeypatch):
    """
    Test branch where inline_data.data is raw bytes and mime_type implies jpg.
    Also ensures when research_id is empty the web_url omits it.
    """
    provider = ImageGeneratorProvider()
    # Provide deterministic filename with .jpg extension
    monkeypatch.setattr(provider, "_generate_image_filename", lambda prompt, index: f"test_jpg_{index}.jpg")
    monkeypatch.setattr(provider, "_generate_alt_text", lambda prompt: "alttext")

    raw = b"JPEGBYTES"
    inline = _InlineData(data=raw, mime_type="image/jpeg")
    part = _Part(inline_data=inline)
    content = _Content(parts=[part])
    candidate = _Candidate(content=content)
    response = _Response(candidates=[candidate])

    def gen_func(model=None, contents=None):
        return response

    provider._client = _Client(gen_func)

    output_path = tmp_path
    result = await provider._generate_with_gemini(
        full_prompt="any",
        output_path=output_path,
        num_images=1,
        research_id="",  # empty to take alternative URL branch
        original_prompt="orig",
    )

    assert len(result) == 1
    expected_file = output_path / "test_jpg_0.jpg"
    assert expected_file.exists()
    with open(expected_file, "rb") as f:
        assert f.read() == raw
    assert result[0]["url"].endswith("/outputs/images/test_jpg_0.jpg")
    assert result[0]["prompt"] == "orig"
    assert result[0]["alt_text"] == "alttext"


@pytest.mark.asyncio
async def test_generate_with_gemini_text_instead_of_image(tmp_path, monkeypatch, caplog):
    """
    Test branch where parts exist but contain text (model refused to return image).
    Should not produce any generated_images and should log a warning.
    """
    provider = ImageGeneratorProvider()
    # generate filename shouldn't be called; still set to safe lambda
    monkeypatch.setattr(provider, "_generate_image_filename", lambda prompt, index: f"unused_{index}.png")
    monkeypatch.setattr(provider, "_generate_alt_text", lambda prompt: "alt")

    part_text = _Part(text="I refuse to generate an image for this prompt because ...")
    content = _Content(parts=[part_text])
    candidate = _Candidate(content=content)
    response = _Response(candidates=[candidate])

    def gen_func(model=None, contents=None):
        return response

    provider._client = _Client(gen_func)

    # capture logs to ensure warning emitted
    caplog.clear()
    result = await provider._generate_with_gemini(
        full_prompt="prompt that causes text",
        output_path=tmp_path,
        num_images=1,
        research_id="rid",
        original_prompt="orig",
    )

    # No images generated
    assert result == []
    # Ensure a warning about model returning text was logged
    found_warning = any("Model returned text instead of image" in r.message for r in caplog.records)
    assert found_warning


@pytest.mark.asyncio
async def test_generate_with_gemini_handles_exception_and_continues(tmp_path, monkeypatch):
    """
    Test branch where the client.generate_content raises an exception (wrapped by asyncio.to_thread),
    ensuring the exception is caught and the generator continues/returns empty list.
    """
    provider = ImageGeneratorProvider()
    monkeypatch.setattr(provider, "_generate_image_filename", lambda prompt, index: f"should_not_exist_{index}.png")
    monkeypatch.setattr(provider, "_generate_alt_text", lambda prompt: "alt")

    def raising_func(model=None, contents=None):
        raise RuntimeError("simulated failure")

    provider._client = _Client(raising_func)

    result = await provider._generate_with_gemini(
        full_prompt="will fail",
        output_path=tmp_path,
        num_images=1,
        research_id="r",
        original_prompt="orig",
    )

    # Should return empty list due to exception being caught and continue
    assert result == []
    # Ensure no file created
    assert not any(tmp_path.iterdir())
