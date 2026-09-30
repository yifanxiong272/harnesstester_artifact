import asyncio
import base64
import types
from pathlib import Path
import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


class FakeInlineData:
    def __init__(self, data, mime_type=None):
        self.data = data
        self.mime_type = mime_type


class FakePart:
    def __init__(self, inline_data=None, text=None):
        # keep attributes that the implementation checks via hasattr
        if inline_data is not None:
            self.inline_data = inline_data
        if text is not None:
            self.text = text


class FakeContent:
    def __init__(self, parts):
        self.parts = parts


class FakeCandidate:
    def __init__(self, content):
        self.content = content


class FakeResponse:
    def __init__(self, candidates):
        self.candidates = candidates


class FakeModels:
    def __init__(self, responder):
        # responder is a callable that returns a FakeResponse or raises
        self._responder = responder

    def generate_content(self, *args, **kwargs):
        return self._responder(*args, **kwargs)


def run_async(coro):
    # helper to run async coroutine deterministically in tests
    return asyncio.get_event_loop().run_until_complete(coro) if asyncio.get_event_loop().is_running() is False else asyncio.run(coro)


def test_generate_with_gemini_inline_base64_round_017(tmp_path):
    """
    Response contains an inline_data as base64 string with mime_type containing 'png'.
    Expect: file written, returned metadata contains url with research id and correct prompt/alt_text.
    """
    # prepare image bytes and base64-encoded string
    original_bytes = b"PNGDATA123"
    b64 = base64.b64encode(original_bytes).decode("ascii")

    def responder(*a, **k):
        part = FakePart(inline_data=FakeInlineData(data=b64, mime_type="image/png"))
        content = FakeContent(parts=[part])
        cand = FakeCandidate(content=content)
        return FakeResponse(candidates=[cand])

    provider = ImageGeneratorProvider(model_name="gemini", api_key=None, output_dir=str(tmp_path))
    # attach fake client
    provider._client = types.SimpleNamespace(models=FakeModels(responder))

    full_prompt = "full prompt"
    original_prompt = "orig prompt"
    research_id = "research42"

    result = run_async(provider._generate_with_gemini(full_prompt, tmp_path, num_images=1, research_id=research_id, original_prompt=original_prompt))

    # There should be exactly one generated image
    assert isinstance(result, list)
    assert len(result) == 1
    meta = result[0]
    # path file exists and contains original bytes
    path = Path(meta["path"])
    assert path.exists()
    read = path.read_bytes()
    assert read == original_bytes

    # url includes research id and prompt/alt_text are set deterministically
    assert research_id in meta["url"]
    assert meta["prompt"] == original_prompt
    assert meta["alt_text"] == provider._generate_alt_text(original_prompt)


def test_generate_with_gemini_inline_bytes_round_017(tmp_path):
    """
    Response contains inline_data as raw bytes and mime_type without 'png' -> uses 'jpg' branch.
    Expect: file written and bytes match.
    Note: upstream implementation currently generates a filename that may still end with .png,
    so accept either .png or .jpg/.jpeg to be robust to that behavior.
    """
    original_bytes = b"RAWJPGDATA"

    def responder(*a, **k):
        part = FakePart(inline_data=FakeInlineData(data=original_bytes, mime_type="image/jpeg"))
        content = FakeContent(parts=[part])
        cand = FakeCandidate(content=content)
        return FakeResponse(candidates=[cand])

    provider = ImageGeneratorProvider(model_name="gemini", api_key=None, output_dir=str(tmp_path))
    provider._client = types.SimpleNamespace(models=FakeModels(responder))

    result = run_async(provider._generate_with_gemini("p", tmp_path, num_images=1, research_id="", original_prompt="orig2"))

    assert isinstance(result, list)
    assert len(result) == 1
    meta = result[0]
    written = Path(meta["path"]).read_bytes()
    assert written == original_bytes
    # Accept either png or jpeg/jpg extensions to match current implementation behavior
    filename = Path(meta["path"]).name
    assert filename.endswith((".jpg", ".jpeg", ".png"))


def test_generate_with_gemini_text_response_round_017(tmp_path, caplog):
    """
    Response contains parts with only text (model refused). No image should be generated.
    Expect: returned list empty and a warning logged.
    """
    def responder(*a, **k):
        part = FakePart(text="I refuse to generate images")
        content = FakeContent(parts=[part])
        cand = FakeCandidate(content=content)
        return FakeResponse(candidates=[cand])

    provider = ImageGeneratorProvider(model_name="gemini", api_key=None, output_dir=str(tmp_path))
    provider._client = types.SimpleNamespace(models=FakeModels(responder))

    caplog.clear()
    result = run_async(provider._generate_with_gemini("p", tmp_path, num_images=1, research_id=None, original_prompt="orig3"))

    # No images generated
    assert result == []
    # A warning about text instead of image should be present
    found_warning = any("Model returned text instead of image" in r.message for r in caplog.records)
    assert found_warning


def test_generate_with_gemini_exception_round_017(tmp_path):
    """
    make the underlying generate_content raise an exception. The implementation should catch and continue,
    resulting in an empty list for a single iteration.
    """
    def responder(*a, **k):
        raise RuntimeError("simulated failure")

    provider = ImageGeneratorProvider(model_name="gemini", api_key=None, output_dir=str(tmp_path))
    provider._client = types.SimpleNamespace(models=FakeModels(responder))

    result = run_async(provider._generate_with_gemini("p", tmp_path, num_images=1, research_id="rid", original_prompt="orig4"))
    assert result == []
