import types
import pytest

import aider.gui as gui


class FakeEmpty:
    def __init__(self):
        self.empty_called = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def empty(self):
        self.empty_called = True


class FakeSt:
    def __init__(self, input_map):
        # input_map: dict mapping keys -> returned text_input value
        self._input_map = dict(input_map)
        self.markdowns = []

    def markdown(self, *args, **kwargs):
        # noop, record for debugging if needed
        self.markdowns.append((args, kwargs))

    def empty(self):
        return FakeEmpty()

    def text_input(self, label, placeholder=None, key=None):
        # deterministic: return value for the provided key
        return self._input_map.get(key)


class FakeScraper:
    def __init__(self, content, print_error=None, playwright_available=False):
        self._content = content
        self.print_error = print_error
        self.playwright_available = playwright_available

    def scrape(self, url):
        return self._content


def make_instance():
    """Create a minimal object compatible with GUI.do_web expectations."""
    inst = types.SimpleNamespace()
    # state must have web_content_num and scraper attributes
    inst.state = types.SimpleNamespace(web_content_num=0, scraper=None)
    # attributes referenced elsewhere
    inst.web_content_empty = None
    inst.web_content = None
    inst.scraper = None
    inst.prompt = None
    inst.prompt_as = None

    # info should be callable and collect messages
    inst.info_messages = []

    def info(msg, echo=False):
        inst.info_messages.append(msg)

    inst.info = info

    return inst


def test_prompt_pending_empty_input_round_048(monkeypatch):
    """
    Exercise the branch where prompt_pending() is True and the text_input returns an empty string.
    This should:
    - create a web_content_empty via st.empty()
    - call web_content_empty.empty()
    - increment state.web_content_num
    - return early because web_content is falsy
    """
    # Arrange
    fake_st = FakeSt({"web_content_0": ""})
    monkeypatch.setattr(gui, "st", fake_st)

    # Ensure no real Scraper is constructed (not needed for early return)
    monkeypatch.setattr(gui, "Scraper", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Scraper should not be used")))
    monkeypatch.setattr(gui, "has_playwright", lambda: False)

    inst = make_instance()

    # prompt_pending True triggers the branch that calls empty() on web_content_empty
    inst.prompt_pending = lambda: True

    # Act
    # call the unbound function directly with our instance
    result = gui.GUI.do_web(inst)

    # Assert
    assert result is None
    # state counter should have been incremented
    assert inst.state.web_content_num == 1
    # web_content_empty should have been created
    assert inst.web_content_empty is not None
    # calling web_content_empty.empty() should have set the flag
    assert getattr(inst.web_content_empty, "empty_called", True) is True
    # web_content is empty string from FakeSt
    assert inst.web_content == ""


def test_scraper_returns_content_round_048(monkeypatch):
    """
    When a URL is provided and the scraper returns non-empty content, GUI.do_web should
    set prompt to a string prefixed with the URL and set prompt_as to 'text'. It should
    also attach a Scraper instance to state.scraper when one was not present.
    """
    url = "http://example.com"
    returned_content = "<html>useful page</html>"

    fake_st = FakeSt({"web_content_0": url})
    monkeypatch.setattr(gui, "st", fake_st)

    # Provide has_playwright value to verify passed-through flag
    monkeypatch.setattr(gui, "has_playwright", lambda: True)

    # Patch Scraper to return our FakeScraper with known behavior
    def scraper_factory(print_error=None, playwright_available=False):
        return FakeScraper(returned_content, print_error=print_error, playwright_available=playwright_available)

    monkeypatch.setattr(gui, "Scraper", scraper_factory)

    inst = make_instance()
    inst.prompt_pending = lambda: False  # skip prompt_pending branch

    # Act
    gui.GUI.do_web(inst)

    # Assert
    assert inst.state.scraper is not None
    # Ensure scraper was constructed with correct flag
    assert getattr(inst.state.scraper, "playwright_available") is True
    # The scraper's print_error should be the instance.info function
    assert getattr(inst.state.scraper, "print_error") == inst.info
    # Prompt should be prefixed with URL and two newlines
    expected = f"{url}\n\n{returned_content}"
    assert inst.prompt == expected
    assert inst.prompt_as == "text"


def test_scraper_returns_blank_round_048(monkeypatch):
    """
    When the scraper returns only whitespace, GUI.do_web should call self.info with the
    'No web content found' message and set web_content to None.
    """
    url = "http://example.com/no-content"

    fake_st = FakeSt({"web_content_0": url})
    monkeypatch.setattr(gui, "st", fake_st)

    monkeypatch.setattr(gui, "has_playwright", lambda: False)

    def scraper_factory(print_error=None, playwright_available=False):
        return FakeScraper("   \n  ", print_error=print_error, playwright_available=playwright_available)

    monkeypatch.setattr(gui, "Scraper", scraper_factory)

    inst = make_instance()
    inst.prompt_pending = lambda: False

    gui.GUI.do_web(inst)

    # Since content is blank/whitespace, prompt should not be set
    assert inst.prompt is None
    # web_content should be reset to None in the else branch
    assert inst.web_content is None
    # info should have been called with a message mentioning the URL
    assert any(f"No web content found for `{url}`." in m for m in inst.info_messages)
