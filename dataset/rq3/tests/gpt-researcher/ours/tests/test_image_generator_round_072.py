import pytest
import asyncio
from typing import Any, Dict, List
from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


@pytest.mark.asyncio
async def test_no_api_key_round_072(caplog, tmp_path):
    """If api_key is falsy, generate_image should warn and return an empty list."""
    # Construct provider with no API key
    provider = ImageGeneratorProvider(model_name="m", api_key="", output_dir=str(tmp_path))

    # Ensure logger warnings are captured
    caplog.clear()

    res = await provider.generate_image(prompt="p", context="c", research_id="r123")

    assert res == []
    # The implementation logs a warning when no API key is configured
    assert any("No API key configured for image generation" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_generate_with_imagen_round_072(tmp_path):
    """When _is_imagen is True, generate_image should call _generate_with_imagen and return its output.
    Also assert _build_enhanced_prompt got the prompt/context/style used by the wrapper.
    """
    provider = ImageGeneratorProvider(model_name="m", api_key="valid-key", output_dir=str(tmp_path))

    # Replace methods that would do I/O or call external services
    called: List[Dict[str, Any]] = []

    async def fake_generate_with_imagen(full_prompt, output_path, num_images, aspect_ratio, research_id):
        # record inputs for assertions
        called.append({
            "full_prompt": full_prompt,
            "output_path": output_path,
            "num_images": num_images,
            "aspect_ratio": aspect_ratio,
            "research_id": research_id,
        })
        return [{"path": str(output_path) + "/img1.png", "meta": {"prompt": full_prompt}}]

    def fake_ensure_client():
        # no-op, just to satisfy the call
        return None

    def fake_ensure_output_dir(research_id: str):
        # return a deterministic path inside tmp_path
        p = tmp_path / (research_id or "default")
        p.mkdir(exist_ok=True)
        return str(p)

    build_calls: List[Dict[str, Any]] = []

    def fake_build_enhanced_prompt(prompt, context, style):
        build_calls.append({"prompt": prompt, "context": context, "style": style})
        return f"ENHANCED: {prompt} | {context} | {style}"

    # Attach fakes to the instance
    provider._ensure_client = fake_ensure_client
    provider._ensure_output_dir = fake_ensure_output_dir
    provider._build_enhanced_prompt = fake_build_enhanced_prompt
    provider._generate_with_imagen = fake_generate_with_imagen

    # Force the imagen path
    provider._is_imagen = True

    out = await provider.generate_image(prompt="a prompt", context="ctx", research_id="rid", aspect_ratio="16:9", num_images=2, style="dark")

    # Assert we got back the fake result and that the stub was invoked with expected args
    assert isinstance(out, list)
    assert out == [{"path": str(tmp_path / "rid") + "/img1.png", "meta": {"prompt": "ENHANCED: a prompt | ctx | dark"}}]
    assert len(called) == 1
    assert called[0]["num_images"] == 2
    assert called[0]["aspect_ratio"] == "16:9"
    assert build_calls and build_calls[0]["style"] == "dark"


@pytest.mark.asyncio
async def test_generate_with_gemini_and_exception_round_072(caplog, tmp_path):
    """When _is_imagen is False, generate_image should call _generate_with_gemini.
    Also ensure that if the underlying generator raises, generate_image logs the error and returns [].
    """
    provider = ImageGeneratorProvider(model_name="m", api_key="valid-key", output_dir=str(tmp_path))

    # Setup no-op client and deterministic output dir
    provider._ensure_client = lambda: None
    provider._ensure_output_dir = lambda research_id: str(tmp_path / (research_id or "g"))

    # Build prompt spy
    built = {}

    def fake_build_enhanced_prompt(prompt, context, style):
        built["value"] = f"GEMINI: {prompt}|{context}|{style}"
        return built["value"]

    # Successful gemini generator
    async def fake_generate_with_gemini(full_prompt, output_path, num_images, research_id, original_prompt):
        return [{"p": output_path + "/g1.png", "orig": original_prompt}]

    # Attach and test the gemini success path
    provider._build_enhanced_prompt = fake_build_enhanced_prompt
    provider._generate_with_gemini = fake_generate_with_gemini
    provider._is_imagen = False

    res = await provider.generate_image(prompt="origPROMPT", context="CTX", research_id="ridG", num_images=1, style="light")
    assert res == [{"p": str(tmp_path / "ridG") + "/g1.png", "orig": "origPROMPT"}]
    assert built.get("value") is not None and "origPROMPT" in built["value"]

    # Now simulate the generator raising an exception to hit the except branch
    async def exploding_generate_with_gemini(*args, **kwargs):
        raise RuntimeError("simulated failure")

    provider._generate_with_gemini = exploding_generate_with_gemini

    caplog.clear()
    # Ensure we capture error logs
    res2 = await provider.generate_image(prompt="x", context="y", research_id="ridX")
    assert res2 == []
    assert any("Image generation failed" in rec.message for rec in caplog.records)
