import pytest
import asyncio
from pathlib import Path
from typing import Any, Dict, List

from gpt_researcher.llm_provider.image.modelslab_image_generator import (
    ModelsLabImageGeneratorProvider,
)


@pytest.mark.asyncio
async def test_no_api_key_round_042(tmp_path: Path):
    """When no API key is configured, generate_image should log/skip and return an empty list.

    Covers branch where self.api_key is falsy (lines ~145-147).
    """
    provider = ModelsLabImageGeneratorProvider(model_id="m-id", api_key=None, output_dir=tmp_path)

    # No network or disk side effects expected; should return empty list deterministically
    results = await provider.generate_image("a prompt without API key")
    assert results == [], "Expected empty result when api_key is not set"


@pytest.mark.asyncio
async def test_request_images_failure_round_042(tmp_path: Path, monkeypatch):
    """If the image request fails (_request_images raises), generate_image should return [] and not raise.

    Covers the exception path from awaiting _request_images (lines ~167-171).
    """
    provider = ModelsLabImageGeneratorProvider(model_id="m-id", api_key="good-key", output_dir=tmp_path)

    # Ensure the provider writes into our temp directory
    monkeypatch.setattr(provider, "_ensure_output_dir", lambda research_id: tmp_path)

    async def fake_request_images(payload: Dict[str, Any]):
        raise RuntimeError("simulated request failure")

    monkeypatch.setattr(provider, "_request_images", fake_request_images)

    results = await provider.generate_image("prompt causing request failure", research_id="rid", num_images=1)
    assert results == [], "Expected empty results when _request_images raises an exception"


@pytest.mark.asyncio
async def test_download_and_save_and_partial_failure_round_042(tmp_path: Path, monkeypatch):
    """Test successful download+save for one image and a download failure for another image.

    - Mocks _request_images to return two URLs.
    - Mocks _download_image to succeed for the first URL and raise for the second.
    - Mocks _generate_filename to produce deterministic filenames.
    - Verifies the saved file contents and returned metadata (including web_url formation when research_id is present),
      and verifies that the failing download does not produce a result entry.

    This covers the successful write path and the download-exception path (lines ~173-199,
    including the branch that appends to `results` and the except branch that logs errors).
    """
    provider = ModelsLabImageGeneratorProvider(model_id="m-id", api_key="good-key", output_dir=tmp_path)

    # Use our tmp_path as the ensured output directory
    monkeypatch.setattr(provider, "_ensure_output_dir", lambda research_id: tmp_path)

    async def fake_request_images(payload: Dict[str, Any]) -> List[str]:
        # Return two image URLs (these are just identifiers for our fake downloader)
        return ["url-success", "url-fail"]

    async def fake_download_image(url: str) -> bytes:
        if url == "url-success":
            return b"IMAGE_BYTES_SUCCESS"
        else:
            raise IOError("simulated download failure")

    def fake_generate_filename(prompt: str, index: int) -> str:
        # deterministic filename pattern for assertions
        return f"img_{index}.png"

    monkeypatch.setattr(provider, "_request_images", fake_request_images)
    monkeypatch.setattr(provider, "_download_image", fake_download_image)
    monkeypatch.setattr(provider, "_generate_filename", fake_generate_filename)

    # Call with research_id to get the /outputs/images/{research_id}/{filename} branch
    results = await provider.generate_image("My prompt for images", research_id="research123", num_images=2)

    # Only first download should succeed, so expect one result
    assert isinstance(results, list)
    assert len(results) == 1, f"Expected 1 successful result, got: {len(results)}"

    res = results[0]
    expected_filename = "img_0.png"
    expected_path = (tmp_path / expected_filename).resolve()

    # File should have been written with the bytes returned by fake_download_image
    assert expected_path.exists(), f"Expected file {expected_path} to be created"
    assert expected_path.read_bytes() == b"IMAGE_BYTES_SUCCESS"

    # Validate metadata fields
    assert res["path"] == str(expected_path)
    assert res["absolute_url"] == str(expected_path)
    assert res["url"] == f"/outputs/images/research123/{expected_filename}"
    assert res["prompt"] == "My prompt for images"
    assert res["alt_text"].startswith("Illustration: My prompt for images")

    # Now also validate the branch when research_id is empty (should produce different web_url)
    # Use a fresh provider instance to avoid state crossover
    provider2 = ModelsLabImageGeneratorProvider(model_id="m-id", api_key="good-key", output_dir=tmp_path)
    monkeypatch.setattr(provider2, "_ensure_output_dir", lambda research_id: tmp_path)

    async def single_request(payload: Dict[str, Any]) -> List[str]:
        return ["url-only"]

    async def single_download(url: str) -> bytes:
        return b"ONLY_ONE"

    def single_filename(prompt: str, index: int) -> str:
        return "single.png"

    monkeypatch.setattr(provider2, "_request_images", single_request)
    monkeypatch.setattr(provider2, "_download_image", single_download)
    monkeypatch.setattr(provider2, "_generate_filename", single_filename)

    results2 = await provider2.generate_image("p2", research_id="", num_images=1)
    assert len(results2) == 1
    res2 = results2[0]
    # When research_id is empty, url should be /outputs/images/{filename}
    assert res2["url"] == "/outputs/images/single.png"
    # file should exist
    assert (tmp_path / "single.png").exists()
    assert (tmp_path / "single.png").read_bytes() == b"ONLY_ONE"
