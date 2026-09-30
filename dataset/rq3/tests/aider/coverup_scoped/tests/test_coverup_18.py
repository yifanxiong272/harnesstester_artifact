# file: aider/gui.py:464-496
# asked: {"lines": [464, 465, 467, 468, 470, 471, 472, 474, 475, 476, 477, 478, 481, 482, 484, 486, 487, 489, 490, 491, 492, 493, 495, 496], "branches": [[467, 468], [467, 470], [470, 471], [470, 474], [481, 482], [481, 484], [486, 487], [486, 489], [490, 491], [490, 495]]}
# gained: {"lines": [464, 465, 467, 468, 470, 471, 472, 474, 475, 476, 477, 478, 481, 484, 486, 487, 489, 490, 491, 492, 493, 495, 496], "branches": [[467, 468], [470, 471], [481, 484], [486, 487], [490, 491], [490, 495]]}

import importlib
import sys
import types
import pytest


class FakeEmpty:
    def __init__(self):
        self.empty_called = False
        self.entered = False

    def empty(self):
        self.empty_called = True

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def make_fake_streamlit(text_input_return):
    """
    Create a fake streamlit module object with the minimal API used by aider.gui.do_web.
    text_input_return can be a string or a callable returning a string.
    """
    mod = types.ModuleType("streamlit")
    mod.markdown_called = []

    def markdown(text):
        mod.markdown_called.append(text)

    mod.markdown = markdown

    # A single FakeEmpty instance to be returned by st.empty()
    fake_empty = FakeEmpty()

    def empty():
        return fake_empty

    mod.empty = empty

    def text_input(label, placeholder=None, key=None):
        if callable(text_input_return):
            return text_input_return(label, placeholder, key)
        return text_input_return

    mod.text_input = text_input

    # Provide a minimal chat_input to avoid accidental calls if module init uses it;
    # return empty string so GUI.__init__ path won't set prompt (we won't call __init__ anyway).
    mod.chat_input = lambda prompt: ""

    # minimal functions used in other parts of module (no-ops)
    mod.write = lambda *a, **k: None
    mod.text = lambda *a, **k: None
    mod.rerun = lambda: None

    # expander used as context manager; provide one that returns a context manager doing nothing
    class _ExpanderCtx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def expander(label):
        return _ExpanderCtx()

    mod.expander = expander

    # Provide cache_resource and cache_data decorators used at import-time in aider.gui
    def _identity_decorator(func=None, **kwargs):
        if func is None:
            def _inner(f):
                return f
            return _inner
        return func

    mod.cache_resource = _identity_decorator
    mod.cache_data = _identity_decorator

    # expose the fake_empty for assertions
    mod._fake_empty = fake_empty

    return mod


def setup_aider_scrape_module(return_content):
    """
    Create a fake aider.scrape module with Scraper and has_playwright and install_playwright.
    Scraper will produce return_content on scrape().
    """
    fake_mod = types.ModuleType("aider.scrape")

    class Scraper:
        def __init__(self, print_error=None, playwright_available=None):
            # store for inspection if needed
            self.print_error = print_error
            self.playwright_available = playwright_available
            self._return = return_content

        def scrape(self, url):
            return self._return

    fake_mod.Scraper = Scraper
    fake_mod.has_playwright = lambda: False
    fake_mod.install_playwright = lambda: None
    return fake_mod


def import_gui_with_fakes(monkeypatch, text_input_return, scrape_return):
    """
    Insert fake streamlit and aider.scrape into sys.modules, remove cached aider.gui,
    then import and return the GUI class and the fake modules for inspection.
    """
    fake_st = make_fake_streamlit(text_input_return)
    fake_scrape = setup_aider_scrape_module(scrape_return)

    # Insert fakes into sys.modules
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setitem(sys.modules, "aider.scrape", fake_scrape)

    # Ensure re-import of aider.gui uses our fake submodule
    if "aider.gui" in sys.modules:
        del sys.modules["aider.gui"]

    gui_module = importlib.import_module("aider.gui")
    GUI = gui_module.GUI
    return GUI, fake_st, fake_scrape


def make_gui_instance(GUI):
    # Create instance without running __init__
    gui = object.__new__(GUI)
    # Minimal attributes expected by do_web
    gui.prompt = None
    gui.prompt_as = "user"
    gui.web_content_empty = None
    gui.web_content = None
    # state object with needed attributes
    gui.state = types.SimpleNamespace(web_content_num=0, scraper=None)
    # capture info messages
    gui._info_msgs = []
    gui.info = lambda message, echo=True: gui._info_msgs.append((message, echo))
    return gui


def test_do_web_with_scraped_content(monkeypatch):
    # Arrange: st.text_input returns a URL, Scraper.scrape returns non-empty content
    url = "https://example.com"
    scraped = "This is the page content."

    GUI, fake_st, fake_scrape = import_gui_with_fakes(
        monkeypatch, text_input_return=url, scrape_return=scraped
    )

    gui = make_gui_instance(GUI)

    # prompt_pending should be True to exercise the branch that empties the placeholder and increments counter
    gui.prompt_pending = lambda: True

    # Act
    gui.do_web()

    # Assert: streamlit.markdown was called (at least once)
    assert fake_st.markdown_called, "st.markdown was not called"

    # web_content_empty should now be the fake empty object and its empty() should have been called
    fake_empty = fake_st._fake_empty
    assert isinstance(fake_empty, FakeEmpty)
    # Because prompt_pending returned True, empty() should have been called
    assert fake_empty.empty_called is True

    # state.web_content_num incremented
    assert gui.state.web_content_num == 1

    # scraper attribute created on the GUI instance
    assert hasattr(gui, "scraper")
    # prompt should be set to "url\n\n<content>"
    assert gui.prompt is not None
    assert gui.prompt.startswith(url + "\n\n")
    assert gui.prompt.endswith(scraped)
    assert gui.prompt_as == "text"

    # No info message should have been logged in this case
    assert gui._info_msgs == []


def test_do_web_with_no_scraped_content(monkeypatch):
    # Arrange: st.text_input returns a URL, Scraper.scrape returns empty content
    url = "https://no-content.example"
    scraped = ""  # empty => triggers the "No web content found" branch

    GUI, fake_st, fake_scrape = import_gui_with_fakes(
        monkeypatch, text_input_return=url, scrape_return=scraped
    )

    gui = make_gui_instance(GUI)

    # prompt_pending True to exercise web_content_empty.empty() and increment
    gui.prompt_pending = lambda: True

    # Act
    gui.do_web()

    # Assert: info was called with the expected message
    assert gui._info_msgs, "info() was not called for empty content"
    msg, echo = gui._info_msgs[-1]
    assert "No web content found for" in msg
    assert url in msg
    # web_content should have been reset to None according to the else branch
    assert gui.web_content is None
    # prompt should not have been set to the url/content
    assert not gui.prompt, "prompt should not be set when no content is found"

    # state.web_content_num incremented
    assert gui.state.web_content_num == 1

    # The GUI should have created a scraper attribute (Scraper instantiated)
    assert hasattr(gui, "scraper")
    # The fake empty's empty() should have been called because prompt_pending returned True
    fake_empty = fake_st._fake_empty
    assert fake_empty.empty_called is True
