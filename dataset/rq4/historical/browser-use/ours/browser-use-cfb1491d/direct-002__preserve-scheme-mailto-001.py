import pytest
from browser_use.browser.session import BrowserSession

class _MockPage:
    def __init__(self):
        self.got_url = None
        # page.url may be referenced in logging paths; provide a stable value
        self.url = "about:blank"

    async def goto(self, url):
        # record exactly what was requested
        self.got_url = url

    async def wait_for_load_state(self):
        # succeed deterministically
        return None


@pytest.mark.asyncio
async def test_probe_001():
    """Direct probe: ensure navigate_to preserves an explicit non-hierarchical scheme.

    This constructs a BrowserSession without running its initializer (object.__new__)
    and injects deterministic, synchronous/async mocks for _is_url_allowed and
    get_current_page. We call navigate_to with whitespace around a 'mailto:' URL
    and assert the mock page.goto received the trimmed original URL (no 'https://' prefix).
    """
    # Create a bare instance without heavy initialization
    session = object.__new__(BrowserSession)

    # Activation condition: allow the URL so navigate_to proceeds
    session._is_url_allowed = lambda u: True

    # Prepare a deterministic mock page and a minimal async getter
    page = _MockPage()

    async def _get_current_page():
        return page

    session.get_current_page = _get_current_page

    # Input: whitespace-padded non-hierarchical scheme URL
    raw_url = "  mailto:alice@example.com  "

    # Exercise the public entrypoint under test
    await session.navigate_to(raw_url)

    # Primary oracle: navigate_to must preserve the explicit 'mailto:' scheme
    assert page.got_url == "mailto:alice@example.com", (
        f"navigate_to mutated explicit scheme: page.goto was called with {page.got_url!r}"
    )
