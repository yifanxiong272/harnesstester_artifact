import asyncio
import tempfile
import types
from pathlib import Path

import pytest

from gpt_researcher.llm_provider.image.modelslab_image_generator import (
    ModelsLabImageGeneratorProvider,
)


def test_no_api_key_round_042():
    """When no API key is set, generate_image should quickly return an empty list."""
    td = tempfile.TemporaryDirectory()
    # constructor signature: (model_id, api_key, output_dir)
    provider = ModelsLabImageGeneratorProvider("m1", "", td.name)

    # Run the async method deterministically
    results = asyncio.run(provider.generate_image("a prompt"))

    assert results == []


def test_request_images_exception_round_042():
    """If _request_images raises, generate_image should catch and return []."""
    td = tempfile.TemporaryDirectory()
    provider = ModelsLabImageGeneratorProvider("m1", "key-xyz", td.name)

    async def bad_request(self, payload):
        raise RuntimeError("simulated request failure")

    # Patch the instance method to avoid any network calls
    provider._request_images = types.MethodType(bad_request, provider)

    results = asyncio.run(
        provider.generate_image("prompt here", context="ctx", research_id="r1", num_images=1)
    )

    assert results == []


def test_success_and_partial_download_failure_and_weburl_variants_round_042():
    """
    Exercise the loop that processes returned image URLs.
    - First provider: returns two urls, first download succeeds, second fails -> one result appended.
    - Verify web_url when research_id is present.
    - Second provider: single url, download succeeds, research_id empty -> web_url uses fallback path.
    """
    # Setup temp output dir
    td1 = tempfile.TemporaryDirectory()
    base1 = Path(td1.name)
    (base1).mkdir(parents=True, exist_ok=True)

    provider1 = ModelsLabImageGeneratorProvider("m1", "key-abc", td1.name)

    # Ensure output dir behavior: return a Path where files will be written
    def ensure_out(research_id):
        dest = base1 / research_id if research_id else base1
        dest.mkdir(parents=True, exist_ok=True)
        return dest

    provider1._ensure_output_dir = ensure_out

    async def request_images_stub(self, payload):
        # return two URLs; the provider code slices to num_images
        return ["http://example.local/1.png", "http://example.local/2.png"]

    async def download_stub(self, url):
        if "1.png" in url:
            return b"IMAGEBYTES1"
        raise RuntimeError("download failed for " + url)

    def gen_filename(prompt, index):
        return f"img_{index}.png"

    provider1._request_images = types.MethodType(request_images_stub, provider1)
    provider1._download_image = types.MethodType(download_stub, provider1)
    provider1._generate_filename = gen_filename

    results1 = asyncio.run(
        provider1.generate_image("Test Prompt", context="ctx", research_id="research42", num_images=2)
    )

    # Only the first image should be present because the second download raises
    assert isinstance(results1, list)
    assert len(results1) == 1

    r = results1[0]
    # path should point to a file placed under our temporary dir
    assert r["path"].endswith("img_0.png")
    assert Path(r["path"]).exists()

    # web url should include the research_id directory
    assert r["url"] == "/outputs/images/research42/img_0.png"
    assert r["prompt"] == "Test Prompt"
    assert r["alt_text"].startswith("Illustration: Test Prompt")

    # --- Now test the branch when research_id is empty (fallback web_url) ---
    td2 = tempfile.TemporaryDirectory()
    base2 = Path(td2.name)
    base2.mkdir(parents=True, exist_ok=True)

    provider2 = ModelsLabImageGeneratorProvider("m1", "key-abc", td2.name)

    def ensure_out2(research_id):
        dest = base2
        dest.mkdir(parents=True, exist_ok=True)
        return dest

    async def request_images_stub2(self, payload):
        return ["http://example.local/single.png"]

    async def download_stub2(self, url):
        return b"IMAGEBYTES_SINGLE"

    def gen_filename2(prompt, index):
        return "solo.png"

    provider2._ensure_output_dir = ensure_out2
    provider2._request_images = types.MethodType(request_images_stub2, provider2)
    provider2._download_image = types.MethodType(download_stub2, provider2)
    provider2._generate_filename = gen_filename2

    results2 = asyncio.run(provider2.generate_image("Another Prompt", context="", research_id="", num_images=1))

    assert len(results2) == 1
    r2 = results2[0]
    assert r2["url"] == "/outputs/images/solo.png"
    assert Path(r2["path"]).exists()
