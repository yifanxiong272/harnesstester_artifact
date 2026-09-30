import pytest

from browser_use.browser import session

# Calling the staticmethod under test via the class for clarity
_is_valid = session.BrowserSession._is_valid_target


def test_is_valid_target_new_tab_page_round_071(monkeypatch):
    # is_new_tab_page should short-circuit url checks and allow known page types
    monkeypatch.setattr(session, "is_new_tab_page", lambda u: True)
    target_info = {"type": "page", "url": "chrome://new-tab-page/"}

    assert _is_valid(target_info) is True


def test_is_valid_target_chrome_error_round_071(monkeypatch):
    # chrome-error:// is allowed only when include_chrome_error is True
    monkeypatch.setattr(session, "is_new_tab_page", lambda u: False)
    target_info = {"type": "tab", "url": "chrome-error://crash"}

    assert _is_valid(target_info, include_chrome_error=True) is True
    # without include_chrome_error it should be rejected
    assert _is_valid(target_info, include_chrome_error=False) is False


def test_is_valid_target_chrome_and_extension_round_071(monkeypatch):
    monkeypatch.setattr(session, "is_new_tab_page", lambda u: False)

    chrome_target = {"type": "page", "url": "chrome://settings/"}
    assert _is_valid(chrome_target, include_chrome=True) is True
    assert _is_valid(chrome_target, include_chrome=False) is False

    ext_target = {"type": "page", "url": "chrome-extension://some/ext.html"}
    assert _is_valid(ext_target, include_chrome_extensions=True) is True
    assert _is_valid(ext_target, include_chrome_extensions=False) is False


def test_is_valid_target_about_blank_round_071(monkeypatch):
    # about:blank is allowed when include_about is True
    monkeypatch.setattr(session, "is_new_tab_page", lambda u: False)
    target_info = {"type": "page", "url": "about:blank"}

    assert _is_valid(target_info, include_about=True) is True
    assert _is_valid(target_info, include_about=False) is False


def test_is_valid_target_http_https_round_071(monkeypatch):
    monkeypatch.setattr(session, "is_new_tab_page", lambda u: False)

    http_target = {"type": "page", "url": "http://example.local/"}
    https_target = {"type": "page", "url": "https://example.local/"}

    # default include_http=True allows both
    assert _is_valid(http_target) is True
    assert _is_valid(https_target) is True

    # disabling http should reject http targets
    assert _is_valid(http_target, include_http=False) is False


def test_is_valid_target_workers_pages_iframes_and_negatives_round_071(monkeypatch):
    monkeypatch.setattr(session, "is_new_tab_page", lambda u: False)

    # worker types allowed only when include_workers True
    worker = {"type": "service_worker", "url": "https://sw.example/"}
    assert _is_valid(worker, include_workers=True) is True
    assert _is_valid(worker, include_workers=False) is False

    # page/tab types allowed when include_pages True
    page = {"type": "page", "url": ""}
    assert _is_valid(page, include_pages=True) is True
    assert _is_valid(page, include_pages=False) is False

    # iframe/webview: when include_iframes True, empty url should be allowed
    iframe = {"type": "iframe", "url": ""}
    assert _is_valid(iframe, include_iframes=True) is True

    # a non-allowed about: page (not about:blank) should be rejected
    odd_about = {"type": "page", "url": "about:srcdoc"}
    assert _is_valid(odd_about, include_about=True) is False
