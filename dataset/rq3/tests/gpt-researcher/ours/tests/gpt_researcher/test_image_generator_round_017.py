import asyncio
import base64
from types import SimpleNamespace
from pathlib import Path
import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider

# Ensure asyncio.to_thread is synchronous/awaitable for tests
async def _fake_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)

@pytest.mark.asyncio
async def test_generate_with_gemini_writes_image_round_017(monkeypatch, tmp_path):
    # Arrange: Create provider instance and deterministic helpers
    provider = ImageGeneratorProvider(model_name="gemini-test", api_key=None, output_dir=str(tmp_path))
    provider.model_name = "gemini-test"
    provider._generate_image_filename = lambda prompt, idx: f"generated_{idx}.png"
    provider._generate_alt_text = lambda prompt: "alt-text-for-test"

    # Build a base64 inline image part
    raw = b"TESTPNGDATA"
    b64 = base64.b64encode(raw).decode("ascii")
    inline_data = SimpleNamespace(data=b64, mime_type="image/png")
    part = SimpleNamespace(inline_data=inline_data)
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    response = SimpleNamespace(candidates=[candidate])

    # Provide a client with a generate_content function
    class Models:
        def generate_content(self, model, contents):
            # Assert the model and contents are forwarded (deterministic)
            assert model == provider.model_name
            assert isinstance(contents, str)
            return response
    client = SimpleNamespace(models=Models())
    provider._client = client

    # Patch asyncio.to_thread used in the implementation
    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    # Act
    out = await provider._generate_with_gemini(
        full_prompt="full prompt",
        output_path=Path(tmp_path),
        num_images=1,
        research_id="research123",
        original_prompt="orig prompt",
    )

    # Assert: one image entry returned and file exists with expected contents
    assert isinstance(out, list)
    assert len(out) == 1
    entry = out[0]
    assert entry["prompt"] == "orig prompt"
    assert entry["alt_text"] == "alt-text-for-test"
    # Verify path file content matches decoded bytes
    written_path = Path(entry["path"])
    assert written_path.exists()
    with open(written_path, "rb") as f:
        assert f.read() == raw
    # Verify URL contains research id
    assert "/research123/" in entry["url"]

@pytest.mark.asyncio
async def test_generate_with_gemini_handles_text_only_parts_round_017(monkeypatch, tmp_path, caplog):
    # Arrange: provider with a part that has text instead of inline_data
    provider = ImageGeneratorProvider(model_name="gemini-test", api_key=None, output_dir=str(tmp_path))
    provider.model_name = "gemini-test"
    provider._generate_image_filename = lambda prompt, idx: f"generated_{idx}.png"
    provider._generate_alt_text = lambda prompt: "alt-text"

    # Part with text only (simulates model refusal)
    part_text = SimpleNamespace(text="Model refused: policy reason")
    content = SimpleNamespace(parts=[part_text])
    candidate = SimpleNamespace(content=content)
    response = SimpleNamespace(candidates=[candidate])

    class Models:
        def generate_content(self, model, contents):
            return response
    provider._client = SimpleNamespace(models=Models())

    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    # Act
    out = await provider._generate_with_gemini(
        full_prompt="prompt",
        output_path=Path(tmp_path),
        num_images=1,
        research_id="",
        original_prompt="orig",
    )

    # Assert: no images generated, empty list returned
    assert out == []
    # And a warning about text instead of image should have been logged
    assert any("Model returned text instead of image" in rec.message for rec in caplog.records)

@pytest.mark.asyncio
async def test_generate_with_gemini_handles_exception_round_017(monkeypatch, tmp_path):
    # Arrange: provider where generate_content raises exception
    provider = ImageGeneratorProvider(model_name="gemini-test", api_key=None, output_dir=str(tmp_path))
    provider.model_name = "gemini-test"
    provider._generate_image_filename = lambda prompt, idx: f"generated_{idx}.png"
    provider._generate_alt_text = lambda prompt: "alt"

    class Models:
        def generate_content(self, model, contents):
            raise RuntimeError("simulated generation failure")
    provider._client = SimpleNamespace(models=Models())

    monkeypatch.setattr(asyncio, "to_thread", _fake_to_thread)

    # Act: should catch and continue, returning empty list
    out = await provider._generate_with_gemini(
        full_prompt="prompt",
        output_path=Path(tmp_path),
        num_images=2,
        research_id=None,
        original_prompt="orig",
    )

    # Assert
    assert out == []
