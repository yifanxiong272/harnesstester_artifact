# file: gpt_researcher/llm_provider/image/image_generator.py:106-154
# asked: {"lines": [118, 119, 120, 123, 124, 127, 128, 132, 135, 136, 139, 142, 143, 144, 146, 147, 149, 150, 151, 152, 153, 154], "branches": [[127, 128], [127, 132]]}
# gained: {"lines": [118, 119, 120, 123, 124, 127, 128, 132, 135, 136, 139, 142, 143, 144, 146, 147, 149, 150, 151, 152, 153, 154], "branches": [[127, 128], [127, 132]]}

import builtins
import io
import types

import pytest

from gpt_researcher.llm_provider.image.image_generator import ImageGeneratorProvider

try:
    from PIL import Image as PILImage
except Exception:  # pragma: no cover - defensive, tests will require PIL
    PILImage = None


def _make_png_bytes(width: int, height: int, color=(255, 0, 0)):
    """Helper to create PNG bytes for an image of given size using Pillow."""
    if PILImage is None:
        pytest.skip("Pillow (PIL) is required for these tests")
    buf = io.BytesIO()
    img = PILImage.new("RGB", (width, height), color)
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_crop_returns_original_if_wide():
    provider = ImageGeneratorProvider()
    # Create a wide image: width/height = 200/100 = 2.0 >= 16/9 (~1.78)
    original = _make_png_bytes(200, 100)
    result = provider._crop_to_landscape(original, target_ratio=16 / 9)
    # Should return original bytes unchanged
    assert result == original


def test_crop_performs_crop_for_tall_images():
    provider = ImageGeneratorProvider()
    # Create a square image 100x100 which is narrower than 16/9 -> will be cropped to landscape height
    original = _make_png_bytes(100, 100)
    result = provider._crop_to_landscape(original, target_ratio=16 / 9)
    # Result should differ from original
    assert result != original
    # Open the resulting bytes and check its dimensions
    img = PILImage.open(io.BytesIO(result))
    width, height = img.size
    expected_new_height = int(100 / (16 / 9))
    assert width == 100
    assert height == expected_new_height


def test_importerror_returns_original(monkeypatch):
    provider = ImageGeneratorProvider()
    original = _make_png_bytes(50, 50)

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Simulate ImportError when attempting to import PIL (or submodules)
        if isinstance(name, str) and name.split(".")[0] == "PIL":
            raise ImportError("Simulated missing PIL")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        result = provider._crop_to_landscape(original, target_ratio=16 / 9)
        # On ImportError the method should return the original bytes
        assert result == original
    finally:
        # monkeypatch will restore builtins.__import__, but ensure the test does not leak on exception
        pass


def test_generic_exception_in_processing_returns_original(monkeypatch):
    provider = ImageGeneratorProvider()
    original = _make_png_bytes(120, 120)

    # Create a fake image object that will cause an exception when saving the cropped image
    class FakeCropped:
        def save(self, output_stream, format=None, optimize=False):
            raise RuntimeError("Simulated save failure")

    class FakeImage:
        def __init__(self, size):
            self.size = size

        def crop(self, box):
            return FakeCropped()

    # Replace PIL.Image.open with a fake that returns our FakeImage
    if PILImage is None:
        pytest.skip("Pillow (PIL) is required for this test")
    monkeypatch.setattr(PILImage, "open", lambda fp: FakeImage((120, 120)))

    # Now calling should trigger the generic exception branch and return the original bytes
    result = provider._crop_to_landscape(original, target_ratio=16 / 9)
    assert result == original
