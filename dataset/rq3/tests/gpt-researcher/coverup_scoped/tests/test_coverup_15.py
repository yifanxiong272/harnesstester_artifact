# file: gpt_researcher/llm_provider/image/modelslab_image_generator.py:123-201
# asked: {"lines": [145, 146, 147, 149, 150, 151, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167, 168, 169, 170, 171, 173, 174, 175, 176, 177, 178, 179, 180, 182, 183, 184, 185, 186, 188, 189, 190, 191, 192, 193, 194, 197, 198, 199, 201], "branches": [[145, 146], [145, 149], [174, 175], [174, 201]]}
# gained: {"lines": [145, 146, 147, 149, 150, 151, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167, 168, 169, 170, 171, 173, 174, 175, 176, 177, 178, 179, 180, 182, 183, 184, 185, 186, 188, 189, 190, 191, 192, 193, 194, 197, 198, 199, 201], "branches": [[145, 146], [145, 149], [174, 175], [174, 201]]}

import asyncio
import os
from pathlib import Path

import pytest

from gpt_researcher.llm_provider.image.modelslab_image_generator import (
    ModelsLabImageGeneratorProvider,
)


@pytest.mark.asyncio
async def test_no_api_key_returns_empty():
    provider = ModelsLabImageGeneratorProvider(api_key="")
    result = await provider.generate_image("test prompt")
    assert result == []


@pytest.mark.asyncio
async def test_generate_image_success_writes_files(tmp_path, monkeypatch):
    # Prepare provider with an API key and output_dir pointing to tmp_path
    provider = ModelsLabImageGeneratorProvider(api_key="APIKEY", output_dir=str(tmp_path))

    out_dir = tmp_path / "research123"

    # _ensure_output_dir should create and return the directory we control
    def _ensure_output_dir(research_id: str = "") -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    provider._ensure_output_dir = _ensure_output_dir

    # _request_images returns two image URLs
    async def _request_images(payload):
        return ["http://example.com/img1.png", "http://example.com/img2.png"]

    provider._request_images = _request_images

    # _download_image returns bytes based on URL
    async def _download_image(url: str) -> bytes:
        return b"BYTES:" + url.encode("utf-8")

    provider._download_image = _download_image

    # deterministic filenames
    def _generate_filename(prompt: str, index: int = 0) -> str:
        return f"file_{index}.png"

    provider._generate_filename = _generate_filename

    # Run generation requesting 2 images and with a research_id
    results = await provider.generate_image("A lovely prompt", research_id="research123", num_images=2)

    # Verify two results saved and returned
    assert len(results) == 2
    for i, res in enumerate(results):
        expected_filename = f"file_{i}.png"
        expected_path = out_dir / expected_filename
        # path exists and file content matches what our _download_image returned
        assert expected_path.exists()
        with open(expected_path, "rb") as fh:
            assert fh.read() == b"BYTES:" + f"http://example.com/img{i+1}.png".encode("utf-8")
        # web URL includes research_id
        assert res["url"] == f"/outputs/images/research123/{expected_filename}"
        # absolute_url is the same as path.resolve()
        assert res["absolute_url"] == str(expected_path.resolve())
        assert res["prompt"] == "A lovely prompt"
        assert res["alt_text"].startswith("Illustration: A lovely prompt")


@pytest.mark.asyncio
async def test_generate_image_handles_partial_download_failure_and_no_research_id(tmp_path):
    provider = ModelsLabImageGeneratorProvider(api_key="KEY2", output_dir=str(tmp_path))

    out_dir = tmp_path / "no_research"
    def _ensure_output_dir(research_id: str = "") -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir
    provider._ensure_output_dir = _ensure_output_dir

    async def _request_images(payload):
        return ["u1", "u2"]
    provider._request_images = _request_images

    async def _download_image(url: str) -> bytes:
        if url == "u1":
            raise RuntimeError("download failed")
        return b"DATA:" + url.encode("utf-8")
    provider._download_image = _download_image

    def _generate_filename(prompt: str, index: int = 0) -> str:
        return f"file_{index}.png"
    provider._generate_filename = _generate_filename

    results = await provider.generate_image("Prompt B", research_id="", num_images=2)

    # First download failed, second succeeded -> only one result
    assert len(results) == 1
    res = results[0]
    # filename for second (index 1)
    assert res["url"] == "/outputs/images/file_1.png"
    expected_file = out_dir / "file_1.png"
    assert expected_file.exists()
    with open(expected_file, "rb") as fh:
        assert fh.read() == b"DATA:u2"
    assert res["prompt"] == "Prompt B"


@pytest.mark.asyncio
async def test_generate_image_request_images_exception_returns_empty(monkeypatch):
    provider = ModelsLabImageGeneratorProvider(api_key="ANOTHERKEY")

    async def _request_images(payload):
        raise ValueError("boom")
    provider._request_images = _request_images

    # Ensure no accidental file writes by stubbing _ensure_output_dir and _download_image
    provider._ensure_output_dir = lambda research_id="": Path("/tmp/should/not/use")
    provider._download_image = lambda url: b""

    results = await provider.generate_image("irrelevant", research_id="r", num_images=1)
    assert results == []
