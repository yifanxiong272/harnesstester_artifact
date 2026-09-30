# file: browser_use/agent/gif.py:287-384
# asked: {"lines": [287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 301, 303, 304, 305, 306, 307, 309, 310, 311, 312, 315, 316, 319, 320, 321, 322, 323, 324, 326, 327, 328, 329, 333, 334, 335, 336, 337, 341, 342, 343, 344, 345, 348, 349, 352, 353, 354, 355, 356, 357, 359, 360, 361, 362, 366, 367, 368, 369, 370, 371, 375, 376, 377, 378, 379, 380, 383, 384], "branches": [[307, 309], [307, 341], [375, 376], [375, 383]]}
# gained: {"lines": [287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 301, 303, 304, 305, 306, 307, 309, 310, 311, 312, 315, 316, 319, 320, 321, 322, 323, 324, 326, 327, 328, 329, 333, 334, 335, 336, 337, 341, 342, 343, 344, 345, 348, 349, 352, 353, 354, 355, 356, 357, 359, 360, 361, 362, 366, 367, 368, 369, 370, 371, 375, 376, 377, 378, 379, 380, 383, 384], "branches": [[307, 309], [375, 376], [375, 383]]}

import importlib
import pytest
from PIL import Image, ImageFont, ImageChops

gif_mod = importlib.import_module("browser_use.agent.gif")


@pytest.fixture(autouse=True)
def patch_helpers(monkeypatch):
    # Ensure deterministic behavior for text decoding and wrapping
    monkeypatch.setattr(gif_mod, "decode_unicode_escapes_to_utf8", lambda s: s)
    # Return the text unchanged so bounding boxes are computed consistently
    monkeypatch.setattr(gif_mod, "_wrap_text", lambda text, font, max_width: text)
    yield


def _make_fonts():
    # Use PIL's default font which works with ImageDraw.textbbox
    f = ImageFont.load_default()
    return f, f


def test_add_overlay_with_rgba_logo(monkeypatch):
    regular_font, title_font = _make_fonts()
    base = Image.new("RGBA", (400, 300), (255, 255, 255, 255))

    # Create an opaque red RGBA logo that will be placed at top-right
    logo = Image.new("RGBA", (40, 20), (255, 0, 0, 255))

    result = gif_mod._add_overlay_to_image(
        base,
        step_number=3,
        goal_text="Test Goal",
        regular_font=regular_font,
        title_font=title_font,
        margin=10,
        logo=logo,
        display_step=True,
    )

    # Result should be RGB and same size
    assert result.mode == "RGB"
    assert result.size == base.size

    # Compute expected logo position (function uses logo_margin = 20)
    logo_margin = 20
    logo_x = base.width - logo.width - logo_margin
    logo_y = logo_margin

    # Pixel within the logo should be red (logo is fully opaque)
    pix = result.getpixel((logo_x + 1, logo_y + 1))
    assert pix[:3] == (255, 0, 0)


def test_add_overlay_with_rgb_logo(monkeypatch):
    regular_font, title_font = _make_fonts()
    base = Image.new("RGBA", (320, 240), (255, 255, 255, 255))

    # Create an RGB (no alpha) green logo to test paste without mask
    logo_rgb = Image.new("RGB", (30, 15), (0, 255, 0))

    result = gif_mod._add_overlay_to_image(
        base,
        step_number=1,
        goal_text="Another Goal",
        regular_font=regular_font,
        title_font=title_font,
        margin=12,
        logo=logo_rgb,
        display_step=True,
    )

    assert result.mode == "RGB"
    assert result.size == base.size

    # Compute expected logo position (function uses logo_margin = 20)
    logo_margin = 20
    logo_x = base.width - logo_rgb.width - logo_margin
    logo_y = logo_margin

    pix = result.getpixel((logo_x + 2, logo_y + 2))
    assert pix[:3] == (0, 255, 0)


def test_add_overlay_without_logo_changes_image(monkeypatch):
    regular_font, title_font = _make_fonts()
    base = Image.new("RGBA", (360, 280), (255, 255, 255, 255))

    result = gif_mod._add_overlay_to_image(
        base,
        step_number=5,
        goal_text="Goal without logo",
        regular_font=regular_font,
        title_font=title_font,
        margin=15,
        logo=None,
        display_step=True,
    )

    # Ensure result differs from the original base image (overlay applied)
    base_rgb = base.convert("RGB")
    diff = ImageChops.difference(result, base_rgb)
    assert diff.getbbox() is not None
