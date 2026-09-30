# file: browser_use/actor/playground/playground.py:23-232
# asked: {"lines": [23, 25, 28, 30, 32, 33, 36, 37, 40, 41, 42, 45, 46, 47, 50, 51, 54, 55, 69, 70, 72, 74, 76, 77, 80, 83, 84, 86, 87, 89, 90, 91, 94, 95, 96, 98, 99, 100, 103, 104, 107, 110, 111, 112, 113, 115, 117, 118, 121, 122, 123, 124, 127, 128, 129, 132, 135, 136, 137, 140, 141, 144, 145, 156, 159, 160, 161, 162, 165, 166, 167, 170, 171, 172, 173, 175, 176, 177, 178, 179, 180, 183, 184, 185, 186, 189, 190, 193, 195, 197, 198, 199, 201, 202, 203, 205, 207, 209, 210, 213, 214, 215, 216, 218, 220, 222, 223, 227, 228, 229, 230, 231, 232], "branches": [[76, 77], [76, 115], [89, 90], [89, 94], [197, 198], [197, 207]]}
# gained: {"lines": [23, 25, 28, 30, 32, 33, 36, 37, 40, 41, 42, 45, 46, 47, 50, 51, 54, 55, 69, 70, 72, 74, 76, 77, 80, 83, 84, 86, 87, 89, 90, 91, 94, 95, 96, 98, 99, 100, 103, 104, 107, 110, 111, 112, 113, 117, 118, 121, 122, 123, 124, 127, 128, 129, 132, 135, 136, 137, 140, 141, 144, 145, 156, 159, 160, 161, 162, 165, 166, 167, 170, 171, 172, 173, 175, 176, 177, 178, 179, 180, 183, 184, 185, 186, 189, 190, 193, 195, 197, 198, 199, 201, 202, 203, 205, 209, 210, 213, 214, 215, 216, 218, 220, 227, 228, 229, 230, 231, 232], "branches": [[76, 77], [89, 90], [197, 198]]}

import asyncio
import json
import builtins
import pytest

# Attempt to import the module under test
import importlib
playground = importlib.import_module("browser_use.actor.playground.playground")


class DummyElement:
    def __init__(self):
        self.hovered = False
        self.focused = False
        self.clicked = False
        self.attrs = {"href": "https://example.org/wiki/Test"}
        self.basic_info = {"nodeName": "A", "boundingBox": {"x": 1, "y": 2, "width": 3, "height": 4}}
        self.filled = None

    async def get_basic_info(self):
        return self.basic_info

    async def get_attribute(self, name):
        return self.attrs.get(name)

    async def hover(self):
        self.hovered = True

    async def focus(self):
        self.focused = True

    async def click(self):
        self.clicked = True

    async def fill(self, text):
        self.filled = text


class DummyMouse:
    def __init__(self):
        self.scrolled = []
        self.moved = []
        self.clicked = []

    async def scroll(self, x=0, y=0, delta_y=0):
        self.scrolled.append((x, y, delta_y))

    async def move(self, x, y):
        self.moved.append((x, y))

    async def click(self, x, y):
        self.clicked.append((x, y))


class DummyPage:
    def __init__(self, url="https://en.wikipedia.org", title="Wikipedia", *,
                 elements=None,
                 elements_raises=False,
                 go_back_raises=False,
                 search_inputs=None):
        self.url = url
        self.title = title
        self._mouse = DummyMouse()
        self._elements = elements if elements is not None else [DummyElement()]
        self._elements_raises = elements_raises
        self._go_back_raises = go_back_raises
        self._search_inputs = search_inputs if search_inputs is not None else []
        self.pressed_keys = []
        self.viewport = None
        self.filled = None

    async def get_url(self):
        return self.url

    async def get_title(self):
        return self.title

    async def screenshot(self):
        # Return bytes; code uses len() on the result
        return b"fake_screenshot_bytes"

    async def set_viewport_size(self, w, h):
        self.viewport = (w, h)

    async def evaluate(self, code, *args):
        # Heuristics on code content to determine return value
        # If the JS returns a JSON-like object, return a JSON string
        code_str = code if isinstance(code, str) else str(code)

        if "Find all article links" in code_str or "sample" in code_str or "links.slice" in code_str:
            # Simulate link counting JS returning JSON string
            info = {"total": len(self._elements), "sample": [{"href": e.attrs.get("href"), "text": "Test"} for e in self._elements[:3]]}
            return json.dumps(info)
        if "document.querySelectorAll('a').length" in code_str and "images" in code_str:
            # page_stats case: return json string
            stats = {
                "url": self.url,
                "title": self.title,
                "links": 5,
                "images": 2,
                "scrollTop": 0,
                "viewportHeight": 800
            }
            return json.dumps(stats)
        if "document.body.scrollHeight" in code_str:
            return 2000
        if "window.pageYOffset" in code_str:
            return 0
        if "x) => x * 2" in code_str or "x * 2" in code_str:
            # args[0] expected
            return args[0] * 2 if args else None
        if "document.title" in code_str and "return" not in code_str:
            return self.title
        # Fallback: return a simple JSON string for unknown evaluates
        return json.dumps({"fallback": True})

    async def get_elements_by_css_selector(self, selector):
        if self._elements_raises:
            raise RuntimeError("Selector failure")
        # Return search inputs for search selectors
        if "input[type=\"search\"]" in selector or "input[name*=\"search\"]" in selector or "input[type='search']" in selector or "input[name*='search']" in selector:
            return self._search_inputs
        return self._elements

    @property
    async def mouse(self):
        return self._mouse

    async def press(self, key):
        self.pressed_keys.append(key)
        # simulate navigation on Enter if search_inputs were used
        if key.lower() == "enter":
            # change url and title to simulate navigation
            self.url = "https://en.wikipedia.org/results"
            self.title = "Search Results"

    async def go_back(self):
        if self._go_back_raises:
            raise RuntimeError("Cannot go back")
        # simulate going back by restoring url/title
        self.url = "https://en.wikipedia.org"
        self.title = "Wikipedia"

    async def focus(self):
        pass

    async def fill(self, text):
        self.filled = text


class DummyBrowser:
    def __init__(self, *, page_factory=None, stop_raises=False):
        self.started = False
        self.stopped = False
        self.start_called = False
        self.stop_called = False
        self.pages = []
        self.page_factory = page_factory or (lambda url=None: DummyPage(url=url or "about:blank"))
        self.stop_raises = stop_raises
        self.closed_pages = []

    async def start(self):
        self.start_called = True
        self.started = True

    async def stop(self):
        self.stop_called = True
        if self.stop_raises:
            raise RuntimeError("stop failed")
        self.stopped = True

    async def new_page(self, url=None):
        p = self.page_factory(url)
        self.pages.append(p)
        return p

    async def get_pages(self):
        return list(self.pages)

    async def close_page(self, page):
        self.closed_pages.append(page)
        try:
            self.pages.remove(page)
        except ValueError:
            pass


class RecordingLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, msg, *args, **kwargs):
        self.infos.append(msg)

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(msg)

    def error(self, msg, *args, **kwargs):
        self.errors.append(msg)


@pytest.mark.asyncio
async def test_main_happy_path(monkeypatch):
    """
    Test the main function on a happy path where:
    - Browser starts/stops successfully
    - There is at least one link element to interact with
    - go_back succeeds
    - A search input is found and used
    """
    logger = RecordingLogger()
    monkeypatch.setattr(playground, "logger", logger)

    # Create a DummyPage with one element and one search input
    element = DummyElement()
    search_input = DummyElement()
    page = DummyPage(url="https://en.wikipedia.org", title="Wikipedia", elements=[element], search_inputs=[search_input])

    # Browser that will return our page for the first new_page call and create a new blank page next
    def page_factory(url=None):
        # If called with url, return the main page; otherwise new blank page
        if url == "https://en.wikipedia.org":
            return page
        return DummyPage(url=url or "about:blank", title="Blank")

    browser = DummyBrowser(page_factory=page_factory, stop_raises=False)

    # Monkeypatch the Browser class inside the module to return our DummyBrowser
    monkeypatch.setattr(playground, "Browser", lambda: browser)

    # Patch input to avoid blocking
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")

    # Run main
    await playground.main()

    # Assertions to verify interactions occurred
    assert browser.start_called is True
    assert browser.stop_called is True
    # The element should have been hovered, focused, and clicked
    assert element.hovered is True
    assert element.focused is True
    assert element.clicked is True
    # New page should have been created and then closed
    assert any(p.title == "Blank" for p in browser.closed_pages)
    # verify that page.press recorded Enter press when search interaction happened
    assert any(k.lower() == "enter" for k in page.pressed_keys), f"pressed_keys was {page.pressed_keys}"

    # Some logging entries should have been recorded
    assert logger.infos, "Expected some info logs"


@pytest.mark.asyncio
async def test_main_error_branches(monkeypatch):
    """
    Test branches where selectors fail and stop() raises an exception to hit warning/error branches.
    - get_elements_by_css_selector raises -> triggers except at lines 117-118
    - go_back raises RuntimeError -> hits the navigation back except branch
    - browser.stop raises -> hits final except block logging error
    """
    logger = RecordingLogger()
    monkeypatch.setattr(playground, "logger", logger)

    # Page that will raise when querying elements and when going back
    page = DummyPage(url="https://en.wikipedia.org", title="Wikipedia",
                     elements=[], elements_raises=True, go_back_raises=True, search_inputs=[])

    def page_factory(url=None):
        # first call will be to the main Wikipedia page
        if url == "https://en.wikipedia.org":
            return page
        return DummyPage(url=url or "about:blank", title="Blank")

    # Browser configured to raise on stop
    browser = DummyBrowser(page_factory=page_factory, stop_raises=True)

    monkeypatch.setattr(playground, "Browser", lambda: browser)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "")

    # Run main; exceptions should be handled inside main, so this should not raise
    await playground.main()

    # Verify that get_elements_by_css_selector raised and warning was logged
    assert logger.warnings or any("interaction failed" in (m or "") or "Link interaction failed" in (m or "") for m in logger.warnings)

    # go_back raised RuntimeError; info about that should be in logs
    assert logger.infos, "Expected info logs (including navigation back failure)"

    # stop raised; error should have been logged in finally block
    assert logger.errors, "Expected errors to be logged when browser.stop() raises"

    # Ensure browser.stop was attempted
    assert browser.stop_called is True
