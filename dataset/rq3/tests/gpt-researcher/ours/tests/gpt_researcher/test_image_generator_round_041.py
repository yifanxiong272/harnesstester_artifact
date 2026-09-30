import asyncio
import sys
import types as _types
from pathlib import Path
from types import SimpleNamespace
import pytest

# Module under test
import importlib
mod = importlib.import_module('gpt_researcher.llm_provider.image.image_generator')

# Helper to inject a fake google.genai.types so the function's local import succeeds
def _ensure_fake_genai_types():
    google = _types.ModuleType('google')
    genai = _types.ModuleType('google.genai')
    genai.types = SimpleNamespace(GenerateImagesConfig=lambda **kwargs: kwargs)
    sys.modules['google'] = google
    sys.modules['google.genai'] = genai

# A simple async to_thread replacement that synchronously calls the provided function
async def _fake_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)


def _make_stub_self(response_obj):
    """Construct a minimal 'self' object matching what _generate_with_imagen expects."""
    # Client whose models.generate_images returns response_obj
    class Models:
        def __init__(self, resp):
            self._resp = resp
        def generate_images(self, model, prompt, config):
            # Return whatever response object was provided
            return self._resp

    class Client:
        def __init__(self, resp):
            self.models = Models(resp)

    # Instance providing required attributes and helper methods
    stub = SimpleNamespace()
    stub.model_name = 'dummy-model'
    stub._client = Client(response_obj)

    # _generate_image_filename(prompt, index) -> filename
    def filename_fn(prompt, index):
        return f"generated_{index}.png"

    # _generate_alt_text(prompt) -> alt_text
    def alt_fn(prompt):
        return f"alt-for-{prompt}"

    stub._generate_image_filename = filename_fn
    stub._generate_alt_text = alt_fn
    return stub


def _make_response_with_images(image_objs):
    """Wrap list of image-like objects into a response object with generated_images attr."""
    resp = SimpleNamespace()
    resp.generated_images = image_objs
    return resp


def test_imagen_no_response_round_041(tmp_path):
    """When the provider's generate_images returns None, function should return empty list."""
    _ensure_fake_genai_types()
    orig_to_thread = mod.asyncio.to_thread
    mod.asyncio.to_thread = _fake_to_thread
    try:
        # response is None
        stub = _make_stub_self(None)
        out = asyncio.run(mod.ImageGeneratorProvider._generate_with_imagen(
            stub,
            full_prompt='nothing',
            output_path=tmp_path,
            num_images=1,
            aspect_ratio='16:9',
            research_id='rid',
        ))
        assert out == [], "Expected empty list when response is falsy"
    finally:
        mod.asyncio.to_thread = orig_to_thread


def test_imagen_generated_nested_and_direct_and_missing_round_041(tmp_path, caplog):
    """Covers nested .image.image_bytes, direct .image_bytes, missing-image path, and URL variants."""
    _ensure_fake_genai_types()
    orig_to_thread = mod.asyncio.to_thread
    mod.asyncio.to_thread = _fake_to_thread
    try:
        # Image 0: nested image bytes
        class Nested:
            def __init__(self, b):
                self.image = SimpleNamespace(image_bytes=b)

        # Image 1: direct image_bytes
        class Direct:
            def __init__(self, b):
                self.image_bytes = b

        # Image 2: missing bytes
        class Missing:
            pass

        img0 = Nested(b'bytes0')
        img1 = Direct(b'bytes1')
        img2 = Missing()

        response = _make_response_with_images([img0, img1, img2])
        stub = _make_stub_self(response)

        # Call with research_id to get path including it
        caplog.clear()
        result_with_rid = asyncio.run(mod.ImageGeneratorProvider._generate_with_imagen(
            stub,
            full_prompt='a prompt',
            output_path=tmp_path,
            num_images=3,
            aspect_ratio='4:3',
            research_id='research42',
        ))

        # We expect two successful images (img0 and img1), img2 should be skipped
        assert len(result_with_rid) == 2
        paths = [item['path'] for item in result_with_rid]
        urls = [item['url'] for item in result_with_rid]
        # The filenames should match generated_0.png and generated_1.png
        assert any('generated_0.png' in p for p in paths)
        assert any('generated_1.png' in p for p in paths)
        # Web URLs should include the research id
        assert all('/outputs/images/research42/' in u for u in urls)

        # Check files were written with expected bytes
        file0 = tmp_path / 'generated_0.png'
        file1 = tmp_path / 'generated_1.png'
        assert file0.exists() and file0.read_bytes() == b'bytes0'
        assert file1.exists() and file1.read_bytes() == b'bytes1'

        # The missing image should have triggered a warning
        assert any('Could not extract image bytes' in rec.message for rec in caplog.records)

        # Now call with no research_id to exercise the other URL branch
        response2 = _make_response_with_images([Direct(b'onlybytes')])
        stub2 = _make_stub_self(response2)
        result_no_rid = asyncio.run(mod.ImageGeneratorProvider._generate_with_imagen(
            stub2,
            full_prompt='other',
            output_path=tmp_path,
            num_images=1,
            aspect_ratio='1:1',
            research_id=None,
        ))
        assert len(result_no_rid) == 1
        assert '/outputs/images/' in result_no_rid[0]['url'] and '/research' not in result_no_rid[0]['url']

    finally:
        mod.asyncio.to_thread = orig_to_thread


def test_imagen_generate_exception_round_041(tmp_path, caplog):
    """If the underlying generate_images raises, the exception is caught and an empty list is returned."""
    _ensure_fake_genai_types()

    # Make a client whose generate_images raises
    class BadModels:
        def generate_images(self, *args, **kwargs):
            raise RuntimeError('boom')

    class BadClient:
        def __init__(self):
            self.models = BadModels()

    stub = SimpleNamespace()
    stub.model_name = 'm'
    stub._client = BadClient()
    # simple helpers
    stub._generate_image_filename = lambda p, i: f'f{i}.png'
    stub._generate_alt_text = lambda p: 'alt'

    # Patch to_thread on the module to actually run the call (and thus raise)
    orig_to_thread = mod.asyncio.to_thread
    mod.asyncio.to_thread = _fake_to_thread
    try:
        caplog.clear()
        out = asyncio.run(mod.ImageGeneratorProvider._generate_with_imagen(
            stub,
            full_prompt='err',
            output_path=tmp_path,
            num_images=1,
            aspect_ratio='16:9',
            research_id='x',
        ))
        # Should return empty list on exception
        assert out == []
        # And an error should be logged
        assert any('Imagen generation failed' in rec.message for rec in caplog.records)
    finally:
        mod.asyncio.to_thread = orig_to_thread
