# file: browser_use/agent/gif.py:35-206
# asked: {"lines": [35, 36, 37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 53, 55, 57, 60, 61, 62, 65, 67, 68, 69, 75, 76, 77, 78, 79, 81, 82, 83, 86, 89, 102, 104, 105, 106, 108, 109, 110, 111, 112, 113, 114, 116, 117, 119, 120, 121, 124, 125, 126, 127, 129, 130, 131, 132, 133, 134, 137, 139, 140, 141, 142, 143, 144, 146, 147, 148, 149, 150, 151, 152, 153, 155, 157, 160, 161, 162, 166, 167, 168, 171, 173, 174, 175, 178, 179, 181, 182, 183, 184, 185, 186, 187, 188, 189, 192, 194, 196, 197, 198, 199, 200, 201, 202, 204, 206], "branches": [[51, 52], [51, 55], [60, 61], [60, 65], [67, 68], [67, 75], [76, 77], [76, 81], [77, 76], [77, 78], [81, 82], [81, 86], [104, 105], [104, 116], [106, 108], [106, 109], [116, 117], [116, 124], [125, 126], [125, 137], [137, 139], [137, 160], [140, 141], [140, 146], [142, 140], [142, 143], [146, 147], [146, 157], [160, 161], [160, 194], [161, 162], [161, 166], [166, 167], [166, 171], [173, 174], [173, 178], [181, 182], [181, 192], [194, 196], [194, 206]]}
# gained: {"lines": [35, 36, 37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 52, 53, 55, 57, 60, 65, 67, 68, 69, 75, 76, 77, 78, 79, 81, 82, 83, 86, 89, 102, 104, 105, 106, 109, 110, 111, 112, 113, 114, 116, 117, 119, 120, 121, 124, 125, 126, 127, 129, 130, 131, 132, 137, 139, 140, 141, 142, 143, 144, 146, 147, 148, 149, 150, 151, 152, 153, 155, 160, 161, 166, 167, 168, 171, 173, 174, 175, 178, 179, 181, 182, 183, 184, 185, 186, 187, 188, 189, 192, 194, 196, 197, 198, 199, 200, 201, 202, 204, 206], "branches": [[51, 52], [51, 55], [60, 65], [67, 68], [67, 75], [76, 77], [76, 81], [77, 76], [77, 78], [81, 82], [81, 86], [104, 105], [104, 116], [106, 109], [116, 117], [116, 124], [125, 126], [125, 137], [137, 139], [137, 160], [140, 141], [142, 143], [146, 147], [160, 161], [160, 194], [161, 166], [166, 167], [166, 171], [173, 174], [173, 178], [181, 182], [194, 196], [194, 206]]}

import base64
import io
import os
from pathlib import Path

import PIL.Image as PilImage
import PIL.ImageFont as PilImageFont
import pytest

from browser_use.agent import gif as gif_mod
from browser_use.browser.views import PLACEHOLDER_4PX_SCREENSHOT


def _make_b64_png(color=(255, 0, 0), size=(10, 10)):
    img = PilImage.new("RGBA", size, color + (255,))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class _State:
    def __init__(self, screenshot_b64, url):
        self._screenshot_b64 = screenshot_b64
        self.url = url

    def get_screenshot(self):
        return self._screenshot_b64


class _ModelOutput:
    def __init__(self, next_goal):
        class CS:
            def __init__(self, next_goal):
                self.next_goal = next_goal

        self.current_state = CS(next_goal)


class _Item:
    def __init__(self, screenshot_b64, url, next_goal=None):
        self.state = _State(screenshot_b64, url)
        self.model_output = _ModelOutput(next_goal) if next_goal is not None else None


class _History:
    def __init__(self, items, screenshots_list):
        self.history = items
        self._screenshots_list = screenshots_list

    def screenshots(self, return_none_if_not_screenshot=True):
        return list(self._screenshots_list)


def test_empty_history_returns(monkeypatch, tmp_path):
    history = _History([], [])
    out = tmp_path / "out1.gif"
    result = gif_mod.create_history_gif("task", history, output_path=str(out))
    assert result is None
    assert not out.exists()


def test_no_screenshots_returns(monkeypatch, tmp_path):
    item = _Item(None, "https://example.com")
    history = _History([item], [])
    out = tmp_path / "out2.gif"
    result = gif_mod.create_history_gif("task", history, output_path=str(out))
    assert result is None
    assert not out.exists()


def test_all_placeholders_returns(monkeypatch, tmp_path):
    placeholder = PLACEHOLDER_4PX_SCREENSHOT
    item = _Item(placeholder, "about:blank")
    history = _History([item], [placeholder])
    out = tmp_path / "out3.gif"
    result = gif_mod.create_history_gif("task", history, output_path=str(out))
    assert result is None
    assert not out.exists()


def test_create_gif_with_overlays_task_and_missing_logo(monkeypatch, tmp_path):
    # Make truetype raise during font discovery, but ensure load_default returns a usable dummy
    monkeypatch.setattr(PilImageFont, "truetype", lambda *a, **k: (_ for _ in ()).throw(OSError("no preferred fonts")))
    class DummyFont:
        pass
    monkeypatch.setattr(PilImageFont, "load_default", lambda *a, **k: DummyFont())

    # Monkeypatch is_new_tab_page to detect new tab pages
    import browser_use.utils as utils_mod

    def fake_is_new_tab_page(url):
        return url.startswith("chrome://newtab") or url == "about:blank"

    monkeypatch.setattr(utils_mod, "is_new_tab_page", fake_is_new_tab_page)

    # Monkeypatch internal helpers to create predictable images for overlays and task frame
    def fake_add_overlay_to_image(image, step_number, goal_text, regular_font, title_font, margin, logo):
        out = image.copy()
        out.putpixel((0, 0), (0, 255, 0, 255))
        return out

    def fake_create_task_frame(task, first_real_screenshot, title_font, regular_font, logo, line_spacing):
        return PilImage.new("RGBA", (10, 10), (0, 0, 255, 255))

    monkeypatch.setattr(gif_mod, "_add_overlay_to_image", fake_add_overlay_to_image)
    monkeypatch.setattr(gif_mod, "_create_task_frame", fake_create_task_frame)

    # Create screenshots: first is a real red image, second is placeholder, third is blue but new tab (skipped)
    red_b64 = _make_b64_png((255, 0, 0))
    blue_b64 = _make_b64_png((0, 0, 255))
    placeholder = PLACEHOLDER_4PX_SCREENSHOT

    item1 = _Item(red_b64, "https://example.com", next_goal="Do X")
    item2 = _Item(placeholder, "about:blank")
    item3 = _Item(blue_b64, "chrome://newtab/")

    history = _History([item1, item2, item3], [red_b64, placeholder, blue_b64])

    out = tmp_path / "out4.gif"
    gif_mod.create_history_gif("My Task", history, output_path=str(out), show_logo=True, show_task=True, show_goals=True)

    assert out.exists()
    img = PilImage.open(str(out))
    assert img.format == "GIF"
    img.close()
    out.unlink()


def test_images_all_skipped_results_in_no_images_warning(monkeypatch, tmp_path):
    import browser_use.utils as utils_mod

    monkeypatch.setattr(utils_mod, "is_new_tab_page", lambda url: True)

    real_b64 = _make_b64_png((123, 123, 123))
    item = _Item(real_b64, "chrome://newtab/")

    history = _History([item], [real_b64])

    out = tmp_path / "out5.gif"
    result = gif_mod.create_history_gif("Task", history, output_path=str(out), show_task=False)
    assert result is None
    assert not out.exists()
