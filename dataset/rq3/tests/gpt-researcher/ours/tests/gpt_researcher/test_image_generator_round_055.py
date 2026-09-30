import builtins
import types
import sys
import io
import pytest

import gpt_researcher.llm_provider.image.image_generator as ig

# Helper to create deterministic fake image bytes that our fake PIL will understand
def make_test_bytes(width: int, height: int) -> bytes:
    # Simple textual encoding so the fake Image.open can determine dimensions
    return f"W{width}H{height}".encode()

class CapturingLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
    def info(self, msg):
        self.infos.append(msg)
    def warning(self, msg):
        self.warnings.append(msg)

def make_fake_pil_module(open_behavior):
    """
    Build a fake PIL module where Image.open uses open_behavior.
    open_behavior should be a callable taking a BytesIO and returning an object
    with .size, .crop(box) and .save(output, format=..., optimize=...).
    """
    pil_mod = types.ModuleType("PIL")
    Image = types.SimpleNamespace()
    Image.open = open_behavior
    pil_mod.Image = Image
    return pil_mod

class FakeImage:
    def __init__(self, width, height):
        self.size = (width, height)
        self._width = width
        self._height = height
    def crop(self, box):
        left, top, right, bottom = box
        new_h = bottom - top
        # return a cropped image object with new size
        return FakeImage(self._width, new_h)
    def save(self, output, format=None, optimize=False):
        # deterministic PNG-like bytes encoding the dimensions for assertions
        output.write(b"PNG" + f"{self._width}x{self._height}".encode())
        output.seek(0)

# Test: when image is already landscape (width/height >= target_ratio) -> returns original bytes
def test_returns_original_when_already_landscape_round_055(monkeypatch):
    original = make_test_bytes(1920, 1080)  # ~1.777... (16/9), should be treated as landscape

    def open_behavior(bio):
        # parse our test bytes and return FakeImage
        raw = bio.getvalue().decode()
        assert raw.startswith("W") and "H" in raw
        w_s, h_s = raw[1:].split("H")
        return FakeImage(int(w_s), int(h_s))

    fake_pil = make_fake_pil_module(open_behavior)
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)

    logger = CapturingLogger()
    # patch logger in target module to capture messages
    monkeypatch.setattr(ig, "logger", logger)

    # call the method directly (does not use self)
    out = ig.ImageGeneratorProvider._crop_to_landscape(object(), original)

    # For a landscape image, we expect the original bytes unchanged and no info crop log
    assert out == original
    assert logger.infos == []
    assert logger.warnings == []

# Test: when image is portrait (width/height < target_ratio) -> crop and return new bytes
def test_crops_to_landscape_round_055(monkeypatch):
    original = make_test_bytes(800, 1200)  # portrait

    def open_behavior(bio):
        raw = bio.getvalue().decode()
        w_s, h_s = raw[1:].split("H")
        return FakeImage(int(w_s), int(h_s))

    fake_pil = make_fake_pil_module(open_behavior)
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)

    logger = CapturingLogger()
    monkeypatch.setattr(ig, "logger", logger)

    out = ig.ImageGeneratorProvider._crop_to_landscape(object(), original, target_ratio=16/9)

    # Expect cropped bytes distinct from original and containing our deterministic PNG marker
    assert out != original
    assert out.startswith(b"PNG")

    # New height should equal int(width / target_ratio)
    expected_new_h = int(800 / (16 / 9))
    assert (str(expected_new_h).encode()) in out

    # Logger should record an info about cropping with original and new dimensions
    assert any("Cropped image from" in msg for msg in logger.infos)
    assert logger.warnings == []

# Test: when PIL is not importable -> ImportError branch -> returns original and logs warning
def test_importerror_returns_original_round_055(monkeypatch):
    original = make_test_bytes(400, 400)

    # Replace builtins.__import__ to raise ImportError for PIL
    real_import = builtins.__import__
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("No PIL here")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    logger = CapturingLogger()
    monkeypatch.setattr(ig, "logger", logger)

    out = ig.ImageGeneratorProvider._crop_to_landscape(object(), original)

    assert out == original
    # Expect a warning about PIL not being available
    assert any("PIL not available" in w for w in logger.warnings)

# Test: unexpected exception in processing (e.g., Image.open raising ValueError) -> returns original and logs
def test_exception_returns_original_round_055(monkeypatch):
    original = make_test_bytes(100, 300)

    def open_behavior_raising(bio):
        raise ValueError("simulated open failure")

    fake_pil = make_fake_pil_module(open_behavior_raising)
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)

    logger = CapturingLogger()
    monkeypatch.setattr(ig, "logger", logger)

    out = ig.ImageGeneratorProvider._crop_to_landscape(object(), original)

    assert out == original
    # Expect a warning containing the simulated exception text
    assert any("simulated open failure" in w for w in logger.warnings)
