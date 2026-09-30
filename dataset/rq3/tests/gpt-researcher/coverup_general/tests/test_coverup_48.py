# file: gpt_researcher/llm_provider/image/image_generator.py:106-154
# asked: {"lines": [118, 119, 120, 123, 124, 127, 128, 132, 135, 136, 139, 142, 143, 144, 146, 147, 149, 150, 151, 152, 153, 154], "branches": [[127, 128], [127, 132]]}
# gained: {"lines": [118, 119, 120, 123, 124, 127, 128, 132, 135, 136, 139, 142, 143, 144, 146, 147, 149, 150, 151, 152, 153, 154], "branches": [[127, 128], [127, 132]]}

import builtins
import io

import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider


def _create_image_bytes(width: int, height: int, color=(255, 0, 0), fmt="PNG") -> bytes:
    """Helper to create an image in memory and return bytes."""
    try:
        from PIL import Image
    except Exception:
        pytest.skip("Pillow (PIL) required for these tests")

    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_crop_no_action_when_already_landscape():
    pytest.importorskip("PIL")

    provider = ImageGeneratorProvider()

    # Create an image with width/height >= 16/9 (landscape)
    width, height = 1600, 800  # ratio = 2.0 > 16/9 (~1.777...)
    img_bytes = _create_image_bytes(width, height)

    out = provider._crop_to_landscape(img_bytes)  # should return original bytes
    assert out == img_bytes, "Expected original bytes when image already landscape"


def test_crop_performs_center_crop_to_landscape():
    PIL = pytest.importorskip("PIL")
    from PIL import Image

    provider = ImageGeneratorProvider()

    # Create a tall image that needs cropping
    width, height = 800, 1000  # ratio = 0.8 < 16/9
    img_bytes = _create_image_bytes(width, height)

    out = provider._crop_to_landscape(img_bytes)
    assert out != img_bytes, "Expected different bytes after cropping"

    # Load returned bytes and verify new size matches expected crop
    out_img = Image.open(io.BytesIO(out))
    expected_new_height = int(width / (16 / 9))
    assert out_img.size == (width, expected_new_height), (
        f"Expected cropped size {(width, expected_new_height)}, got {out_img.size}"
    )


def test_importerror_returns_original(monkeypatch):
    provider = ImageGeneratorProvider()

    # Create an image bytes using real PIL if available; if not, create some dummy bytes
    try:
        img_bytes = _create_image_bytes(800, 1000)
    except pytest.SkipTest:
        img_bytes = b"dummy-bytes"

    # Monkeypatch builtins.__import__ to raise ImportError for PIL imports
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("Simulated missing PIL")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    out = provider._crop_to_landscape(img_bytes)
    # Since PIL import fails, should return the original bytes untouched
    assert out == img_bytes, "When PIL is missing, original bytes should be returned"


def test_generic_exception_during_processing_returns_original(monkeypatch):
    PIL = pytest.importorskip("PIL")
    from PIL import Image

    provider = ImageGeneratorProvider()
    img_bytes = _create_image_bytes(800, 1000)

    # Monkeypatch Image.open to raise a runtime error to trigger the generic exception branch
    def raising_open(*args, **kwargs):
        raise RuntimeError("simulated processing failure")

    monkeypatch.setattr(Image, "open", raising_open)

    out = provider._crop_to_landscape(img_bytes)
    assert out == img_bytes, "When Image.open raises, original bytes should be returned"
