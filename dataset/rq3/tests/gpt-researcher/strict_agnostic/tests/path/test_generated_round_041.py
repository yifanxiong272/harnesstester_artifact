import asyncio
import pytest
from types import SimpleNamespace
from pathlib import Path
from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


@pytest.mark.asyncio
async def test_generate_with_imagen_success_round_041(tmp_path, monkeypatch):
    """Verify that images with both nested image.image.image_bytes and top-level image_bytes
    are written to disk and returned, while entries missing bytes are skipped.
    """
    # Make asyncio.to_thread run the function synchronously for determinism
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    provider = ImageGeneratorProvider(model_name="m", api_key="k", output_dir=str(tmp_path))

    # Three generated image objects: one with image.image.image_bytes, one with image_bytes,
    # and one missing bytes (should be skipped)
    img1 = SimpleNamespace(image=SimpleNamespace(image_bytes=b'AAA'))
    img2 = SimpleNamespace(image_bytes=b'BBB')
    img3 = SimpleNamespace()  # no bytes -> should trigger warning and be skipped

    def fake_generate_images(model, prompt, config):
        return SimpleNamespace(generated_images=[img1, img2, img3])

    # Attach a deterministic fake client (no network)
    provider._client = SimpleNamespace(models=SimpleNamespace(generate_images=fake_generate_images))

    result = await provider._generate_with_imagen(
        full_prompt="my prompt",
        output_path=tmp_path,
        num_images=3,
        aspect_ratio="16:9",
        research_id="rid",
    )

    # Two images should have been produced (img3 skipped)
    assert isinstance(result, list)
    assert len(result) == 2

    # Check that files were written and bytes match
    expected_bytes = [b'AAA', b'BBB']
    for item, expected in zip(result, expected_bytes):
        p = Path(item["path"])
        assert p.exists()
        assert p.read_bytes() == expected
        # url should include research id when provided
        assert "/outputs/images/rid/" in item["url"]
        assert item["prompt"] == "my prompt"
        assert "alt_text" in item


@pytest.mark.asyncio
async def test_generate_with_imagen_no_research_id_round_041(tmp_path, monkeypatch):
    """Verify web_url formatting when research_id is None (no research segment in URL)."""
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    provider = ImageGeneratorProvider(model_name="m", api_key="k", output_dir=str(tmp_path))

    img = SimpleNamespace(image_bytes=b'CCC')

    def fake_generate_images(model, prompt, config):
        return SimpleNamespace(generated_images=[img])

    provider._client = SimpleNamespace(models=SimpleNamespace(generate_images=fake_generate_images))

    result = await provider._generate_with_imagen(
        full_prompt="p2",
        output_path=tmp_path,
        num_images=1,
        aspect_ratio="1:1",
        research_id=None,
    )

    assert len(result) == 1
    # When research_id is None, URL should not contain the research id segment
    assert result[0]["url"].startswith("/outputs/images/")
    assert "/outputs/images/None/" not in result[0]["url"]


@pytest.mark.asyncio
async def test_generate_with_imagen_exception_round_041(monkeypatch, tmp_path):
    """If the underlying generate_images raises, the provider should catch and return an empty list."""
    async def fake_to_thread(func, *args, **kwargs):
        # Execute and propagate the exception into the async context so the provider's try/except can catch it
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    provider = ImageGeneratorProvider(model_name="m", api_key="k", output_dir=str(tmp_path))

    def bad_generate(model, prompt, config):
        raise RuntimeError("boom")

    provider._client = SimpleNamespace(models=SimpleNamespace(generate_images=bad_generate))

    result = await provider._generate_with_imagen(
        full_prompt="p",
        output_path=tmp_path,
        num_images=1,
        aspect_ratio="1:1",
        research_id="rid",
    )

    # Exception path returns empty list (and does not raise out of the provider)
    assert result == []
