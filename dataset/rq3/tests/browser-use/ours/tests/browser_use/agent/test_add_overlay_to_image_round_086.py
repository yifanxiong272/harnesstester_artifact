import pytest
from PIL import Image, ImageFont, ImageDraw

from browser_use.agent import gif as gif_mod


def _make_rgba_image(size=(200, 150), color=(0, 0, 255, 255)):
    return Image.new('RGBA', size, color)


def test_add_overlay_with_step_no_logo_round_086(monkeypatch):
    # Arrange: base image and predictable fonts
    image = _make_rgba_image((200, 150), (0, 0, 255, 255))
    font = ImageFont.load_default()

    # Force deterministic wrapped goal text
    monkeypatch.setattr(gif_mod, '_wrap_text', lambda goal_text, font_arg, max_width: 'Goal')

    # Act: call with display_step True and no logo
    result = gif_mod._add_overlay_to_image(
        image=image,
        step_number=3,
        goal_text='Goal',
        regular_font=font,
        title_font=font,
        margin=10,
        logo=None,
        display_step=True,
    )

    # Assert: returned image has expected mode/size and that overlay modified bottom-left area
    assert result.mode == 'RGB'
    assert result.size == image.size

    # Recompute step area coordinates the function used to draw the step box
    tmp_draw = ImageDraw.Draw(Image.new('RGBA', image.size))
    step_text = str(3)
    step_bbox = tmp_draw.textbbox((0, 0), step_text, font=font)
    step_width = step_bbox[2] - step_bbox[0]
    step_height = step_bbox[3] - step_bbox[1]
    x_step = 10 + 10
    y_step = image.height - 10 - step_height - 10

    # Original background color in RGB
    original_rgb = (0, 0, 255)

    # Pixel at a location inside the expected step background should not equal the original background
    px = result.getpixel((x_step + 1, max(0, y_step + 1)))
    assert px != original_rgb


def test_add_overlay_with_step_and_logo_round_086(monkeypatch):
    # Arrange: larger image and an opaque red RGBA logo
    image = _make_rgba_image((300, 200), (0, 128, 0, 255))
    font = ImageFont.load_default()
    logo = Image.new('RGBA', (40, 30), (255, 0, 0, 255))  # fully opaque red logo

    # Make wrapped goal deterministic and multi-line to exercise multiline drawing
    monkeypatch.setattr(gif_mod, '_wrap_text', lambda goal_text, font_arg, max_width: 'Long Goal\nLine2')

    # Act: call with display_step True and a logo to hit the logo branch
    result = gif_mod._add_overlay_to_image(
        image=image,
        step_number=7,
        goal_text='Long Goal',
        regular_font=font,
        title_font=font,
        margin=20,
        logo=logo,
        display_step=True,
    )

    # Assert: result properties and presence of logo pixels in top-right region
    assert result.mode == 'RGB'
    assert result.size == image.size

    # Compute expected logo placement used by the function
    logo_margin = 20
    logo_x = image.width - logo.width - logo_margin
    logo_y = logo_margin

    # Pixel where logo was pasted should be red (logo is opaque)
    px_logo = result.getpixel((logo_x + 1, logo_y + 1))
    assert px_logo[0] > 200 and px_logo[1] < 50 and px_logo[2] < 50


def test_add_overlay_display_step_false_raises_round_086(monkeypatch):
    # When display_step is False, the function references y_step later which is only set
    # in the display_step branch. This should raise an UnboundLocalError in the current implementation.
    image = _make_rgba_image((200, 150), (10, 10, 10, 255))
    font = ImageFont.load_default()

    # Keep wrapped text deterministic
    monkeypatch.setattr(gif_mod, '_wrap_text', lambda goal_text, font_arg, max_width: 'Goal')

    with pytest.raises(UnboundLocalError):
        gif_mod._add_overlay_to_image(
            image=image,
            step_number=1,
            goal_text='Goal',
            regular_font=font,
            title_font=font,
            margin=10,
            logo=None,
            display_step=False,
        )
