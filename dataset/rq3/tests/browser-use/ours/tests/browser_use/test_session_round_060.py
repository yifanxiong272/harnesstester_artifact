import types
import pytest
import urllib.parse as _urllib_parse

from types import SimpleNamespace

import browser_use.browser.session as session_mod


class FakeTabInfo:
    def __init__(self, *, target_id, url, title, parent_target_id=None):
        # match the construction signature used in the code under test
        self.target_id = target_id
        self.url = url
        self.title = title
        self.parent_target_id = parent_target_id

    def __repr__(self):
        return f"FakeTabInfo(target_id={self.target_id!r}, url={self.url!r}, title={self.title!r})"


class DummyLogger:
    def __init__(self):
        self.last_debug = None

    def debug(self, msg):
        # store debug messages so tests can assert that logging was invoked when exceptions occur
        self.last_debug = msg


@pytest.mark.asyncio
async def test_get_tabs_none_round_060():
    """When session_manager is not present, get_tabs should return an empty list."""
    fake_self = SimpleNamespace(session_manager=None, logger=DummyLogger())

    # Call the async function unbound, passing our dummy self
    tabs = await session_mod.BrowserSession.get_tabs(fake_self)
    assert tabs == []


@pytest.mark.asyncio
async def test_get_tabs_various_target_types_round_060(monkeypatch):
    """Covers new-tab, chrome:// and normal PDF-title extraction flows.

    - new-tab pages use empty title
    - chrome:// pages with no title use the URL as title
    - pdf pages extract filename from URL
    - a target that raises when accessing .title triggers the outer except fallback
    """
    # Patch module-level collaborators so we don't depend on other modules or heavy objects
    monkeypatch.setattr(session_mod, "TabInfo", FakeTabInfo)
    monkeypatch.setattr(session_mod, "_log_pretty_url", lambda u: u)

    # Define is_new_tab_page to detect about: new-tab style URLs
    monkeypatch.setattr(session_mod, "is_new_tab_page", lambda url: isinstance(url, str) and url.startswith("about:"))

    # Targets:
    t_newtab = SimpleNamespace(target_id="t1", url="about:newtab", title="OldTitle")
    t_chrome = SimpleNamespace(target_id="t2", url="chrome://settings", title="")
    t_pdf = SimpleNamespace(target_id="t3", url="https://example.com/path/doc.pdf", title="")

    # target that raises when accessing title - to exercise outer except fallback
    class TitleRaises:
        def __init__(self, target_id, url):
            self.target_id = target_id
            self.url = url

        @property
        def title(self):
            raise RuntimeError("boom when reading title")

    t_broken_title = TitleRaises("t4", "chrome://extensions")

    targets = [t_newtab, t_chrome, t_pdf, t_broken_title]

    fake_session_manager = SimpleNamespace(get_all_page_targets=lambda: targets)
    fake_self = SimpleNamespace(session_manager=fake_session_manager, logger=DummyLogger())

    tabs = await session_mod.BrowserSession.get_tabs(fake_self)

    # Expect 4 tabs returned (one per target)
    assert len(tabs) == 4

    # new-tab: title forced to empty string
    assert tabs[0].target_id == "t1"
    assert tabs[0].url == "about:newtab"
    assert tabs[0].title == ""

    # chrome:// with empty title -> title becomes the URL
    assert tabs[1].target_id == "t2"
    assert tabs[1].url == "chrome://settings"
    assert tabs[1].title == "chrome://settings"

    # pdf: title empty but URL endswith .pdf -> filename used
    assert tabs[2].target_id == "t3"
    assert tabs[2].url == "https://example.com/path/doc.pdf"
    assert tabs[2].title == "doc.pdf"

    # broken .title access triggers except -> fallback path uses chrome:// -> title set to URL
    assert tabs[3].target_id == "t4"
    assert tabs[3].url == "chrome://extensions"
    assert tabs[3].title == "chrome://extensions"


@pytest.mark.asyncio
async def test_get_tabs_pdf_urlparse_error_round_060(monkeypatch):
    """If urllib.parse.urlparse raises while handling a PDF, the inner except should be exercised and
    the code should continue without crashing (title remains unchanged / empty).
    """
    monkeypatch.setattr(session_mod, "TabInfo", FakeTabInfo)
    monkeypatch.setattr(session_mod, "_log_pretty_url", lambda u: u)

    # Make is_new_tab_page always false for this test
    monkeypatch.setattr(session_mod, "is_new_tab_page", lambda url: False)

    # Patch urllib.parse.urlparse to raise to trigger the inner except block
    def raising_urlparse(u):
        raise ValueError("urlparse failed")

    monkeypatch.setattr(_urllib_parse, "urlparse", raising_urlparse)

    t_pdf_bad = SimpleNamespace(target_id="t5", url="https://example.com/broken.pdf", title="")
    fake_session_manager = SimpleNamespace(get_all_page_targets=lambda: [t_pdf_bad])
    fake_self = SimpleNamespace(session_manager=fake_session_manager, logger=DummyLogger())

    tabs = await session_mod.BrowserSession.get_tabs(fake_self)

    assert len(tabs) == 1
    # Since urlparse raised, the inner handler's except path executes and does not set a filename
    # The code leaves title as empty string in this case
    assert tabs[0].target_id == "t5"
    assert tabs[0].url == "https://example.com/broken.pdf"
    assert tabs[0].title == ""
