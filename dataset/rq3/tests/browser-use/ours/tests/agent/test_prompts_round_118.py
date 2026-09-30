import types

import pytest

from browser_use.agent.prompts import AgentMessagePrompt


class DummyDOM:
    def __init__(self, text):
        self._text = text

    def llm_representation(self, include_attributes=True):
        # match the call signature used in the code under test
        return self._text


class PageInfo:
    def __init__(self, pixels_above, pixels_below, viewport_height):
        self.pixels_above = pixels_above
        self.pixels_below = pixels_below
        self.viewport_height = viewport_height


class Tab:
    def __init__(self, url, title, target_id):
        self.url = url
        self.title = title
        self.target_id = target_id


class BrowserState:
    def __init__(
        self,
        dom_text,
        url="",
        title="",
        tabs=None,
        page_info=None,
        is_pdf_viewer=False,
        recent_events=None,
        closed_popup_messages=None,
    ):
        self.dom_state = DummyDOM(dom_text)
        self.url = url
        self.title = title
        self.tabs = tabs or []
        self.page_info = page_info
        self.is_pdf_viewer = is_pdf_viewer
        self.recent_events = recent_events or []
        self.closed_popup_messages = closed_popup_messages or []


def make_prompt_instance():
    # Create an AgentMessagePrompt instance without running __init__ and set attributes manually
    inst = AgentMessagePrompt.__new__(AgentMessagePrompt)
    # sensible defaults
    inst.include_attributes = True
    inst.max_clickable_elements_length = 1000
    inst.include_recent_events = False
    # browser_state will be set by tests
    inst.browser_state = None
    return inst


def bind_stats(inst, stats):
    def _extract_page_statistics(self):
        return stats

    inst._extract_page_statistics = types.MethodType(_extract_page_statistics, inst)


def test_skeleton_images_shadow_current_tab_round_118():
    """
    - Trigger the skeleton/placeholder branch (total_elements > 20 and low text_chars)
    - Trigger shadow and images additions
    - Provide exactly one tab matching url/title to set a current tab id
    - Elements text non-empty and short (no truncation)
    """
    inst = make_prompt_instance()

    stats = {
        "total_elements": 25,
        "text_chars": 50,  # less than 25*5 = 125 -> skeleton branch
        "links": 3,
        "interactive_elements": 2,
        "iframes": 0,
        "shadow_open": 1,
        "shadow_closed": 0,
        "images": 2,
    }
    bind_stats(inst, stats)

    # Provide DOM text so elements_text is non-empty
    bs = BrowserState(
        dom_text="<div>clickable</div>",
        url="https://example.com/page",
        title="Example Page",
        tabs=[Tab("https://example.com/page", "Example Page", "target_123456"), Tab("https://other", "Other", "t2")],
        page_info=None,
        is_pdf_viewer=False,
    )
    inst.browser_state = bs
    inst.max_clickable_elements_length = 200  # no truncation

    out = inst._get_browser_state_description()

    # Assertions: skeleton notice, shadow, images, total elements, current tab, start/end markers
    assert "skeleton/placeholder" in out or "skeleton" in out
    assert "1 shadow(open)" in out
    assert ", 2 images" in out
    assert "25 total elements" in out
    # last 4 of target_123456 are '3456'
    assert "Current tab: 3456" in out
    assert "[Start of page]" in out
    assert "[End of page]" in out


def test_pdf_recent_closedpopups_empty_elements_round_118():
    """
    - Trigger the small-page branch (total_elements < 10)
    - Make dom_state return empty string -> elements_text becomes 'empty page'
    - Set is_pdf_viewer True to exercise PDF guidance text
    - Set include_recent_events True and provide recent_events
    - Provide closed_popup_messages to exercise closed popup formatting
    """
    inst = make_prompt_instance()

    stats = {
        "total_elements": 5,
        "text_chars": 200,
        "links": 1,
        "interactive_elements": 0,
        "iframes": 0,
        "shadow_open": 0,
        "shadow_closed": 0,
        "images": 0,
    }
    bind_stats(inst, stats)

    bs = BrowserState(
        dom_text="",  # will cause elements_text == '' -> becomes 'empty page'
        url="https://pdf.example",
        title="PDF Example",
        tabs=[],
        page_info=None,
        is_pdf_viewer=True,
        recent_events=["click", "navigate"],
        closed_popup_messages=["Are you sure?"],
    )
    inst.browser_state = bs
    inst.include_recent_events = True

    out = inst._get_browser_state_description()

    # Assertions for pdf guidance and recent events and closed popups and empty page text
    assert "PDF viewer cannot be rendered" in out
    assert "Use the read_file action" in out
    assert "Recent browser events" in out
    assert "Auto-closed JavaScript dialogs:" in out
    assert "Are you sure?" in out
    assert "empty page" in out


def test_truncation_and_page_info_scroll_hint_round_118():
    """
    - Trigger truncation of elements_text by setting a very small max_clickable_elements_length
    - Provide page_info with pages_below > 0.2 to include the scroll down hint
    - Ensure pages_above == 0 so we still add a [Start of page] marker but not [End of page]
    """
    inst = make_prompt_instance()

    # Use stats that do not trigger skeleton branch
    stats = {
        "total_elements": 15,
        "text_chars": 200,
        "links": 5,
        "interactive_elements": 3,
        "iframes": 1,
        "shadow_open": 0,
        "shadow_closed": 0,
        "images": 0,
    }
    bind_stats(inst, stats)

    long_dom = "A" * 50  # long enough to be truncated
    # pixels_below large relative to viewport_height to create pages_below > 0.2
    page_info = PageInfo(pixels_above=0, pixels_below=1000, viewport_height=400)
    bs = BrowserState(
        dom_text=long_dom,
        url="https://long.example",
        title="Long",
        tabs=[],
        page_info=page_info,
        is_pdf_viewer=False,
    )
    inst.browser_state = bs
    inst.max_clickable_elements_length = 10  # force truncation

    out = inst._get_browser_state_description()

    # Assert truncation marker appears in the 'Interactive elements' header
    assert "truncated to 10 characters" in out
    # Assert scroll hint text from page_info was appended
    assert "scroll down to reveal more content" in out
    # Because pages_above == 0, we should see a start marker; because pages_below > 0, end marker should NOT be present
    assert "[Start of page]" in out
