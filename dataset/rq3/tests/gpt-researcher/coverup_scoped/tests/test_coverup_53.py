# file: gpt_researcher/llm_provider/image/image_generator.py:225-266
# asked: {"lines": [247, 248, 249, 251, 252, 255, 256, 257, 259, 260, 261, 263, 264, 265, 266], "branches": [[247, 248], [247, 251], [260, 261], [260, 263]]}
# gained: {"lines": [247, 248, 249, 251, 252, 255, 256, 257, 259, 260, 261, 263, 264, 265, 266], "branches": [[247, 248], [247, 251], [260, 261], [260, 263]]}

import asyncio
from pathlib import Path

import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


@pytest.mark.asyncio
async def test_generate_image_no_api_key(monkeypatch):
    # Ensure environment variables are not set so provider has no api_key
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = ImageGeneratorProvider(api_key=None)
    # Sanity: constructor should result in no api_key
    assert provider.api_key is None

    result = await provider.generate_image("a prompt")
    assert result == [], "Expected empty list when no API key is configured"


@pytest.mark.asyncio
async def test_generate_image_imagen_exception(monkeypatch, tmp_path):
    # Use an imagen model so _is_imagen is True
    provider = ImageGeneratorProvider(model_name="imagen-4.0-generate-001", api_key="dummy", output_dir=str(tmp_path))

    called = {}

    # Patch _ensure_client to record it was called
    def fake_ensure_client():
        called["ensure_client"] = True

    # Patch _ensure_output_dir to record and return tmp_path
    def fake_ensure_output_dir(research_id: str = "") -> Path:
        called["ensure_output_dir"] = research_id
        return tmp_path

    # Patch prompt builder
    def fake_build_enhanced_prompt(prompt: str, context: str = "", style: str = "dark"):
        called["build_enhanced_prompt"] = (prompt, context, style)
        return "ENHANCED_PROMPT"

    # Async generator that raises to hit the exception branch
    async def fake_generate_with_imagen(full_prompt, output_path, num_images, aspect_ratio, research_id):
        called["generate_with_imagen_called"] = True
        raise RuntimeError("simulated imagen failure")

    monkeypatch.setattr(provider, "_ensure_client", fake_ensure_client)
    monkeypatch.setattr(provider, "_ensure_output_dir", fake_ensure_output_dir)
    monkeypatch.setattr(provider, "_build_enhanced_prompt", fake_build_enhanced_prompt)
    monkeypatch.setattr(provider, "_generate_with_imagen", fake_generate_with_imagen)

    result = await provider.generate_image("prompt", context="ctx", research_id="rid", aspect_ratio="16:9", num_images=1, style="dark")

    assert result == [], "Expected empty list on imagen generation exception"
    assert called.get("ensure_client") is True
    assert called.get("ensure_output_dir") == "rid"
    assert called.get("build_enhanced_prompt") == ("prompt", "ctx", "dark")
    assert called.get("generate_with_imagen_called") is True


@pytest.mark.asyncio
async def test_generate_image_gemini_exception(monkeypatch, tmp_path):
    # Use a gemini model so _is_imagen is False
    provider = ImageGeneratorProvider(model_name="models/gemini-2.5-flash-image", api_key="dummy", output_dir=str(tmp_path))

    called = {}

    def fake_ensure_client():
        called["ensure_client"] = True

    def fake_ensure_output_dir(research_id: str = "") -> Path:
        called["ensure_output_dir"] = research_id
        return tmp_path

    def fake_build_enhanced_prompt(prompt: str, context: str = "", style: str = "dark"):
        called["build_enhanced_prompt"] = (prompt, context, style)
        return "ENHANCED_PROMPT_GEMINI"

    async def fake_generate_with_gemini(full_prompt, output_path, num_images, research_id, original_prompt):
        called["generate_with_gemini_called"] = (full_prompt, str(output_path), num_images, research_id, original_prompt)
        raise ValueError("simulated gemini failure")

    monkeypatch.setattr(provider, "_ensure_client", fake_ensure_client)
    monkeypatch.setattr(provider, "_ensure_output_dir", fake_ensure_output_dir)
    monkeypatch.setattr(provider, "_build_enhanced_prompt", fake_build_enhanced_prompt)
    monkeypatch.setattr(provider, "_generate_with_gemini", fake_generate_with_gemini)

    result = await provider.generate_image("gprompt", context="gctx", research_id="grid", aspect_ratio="1:1", num_images=2, style="light")

    assert result == [], "Expected empty list on gemini generation exception"
    assert called.get("ensure_client") is True
    assert called.get("ensure_output_dir") == "grid"
    assert called.get("build_enhanced_prompt") == ("gprompt", "gctx", "light")
    assert "generate_with_gemini_called" in called
    gen_args = called["generate_with_gemini_called"]
    assert gen_args[2] == 2  # num_images passed correctly
    assert gen_args[3] == "grid"  # research_id passed correctly
    assert gen_args[4] == "gprompt"  # original prompt passed correctly
