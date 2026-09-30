import sys
import types
from types import ModuleType
from aider.scrape import Scraper

# Helper to inject a fake playwright.sync_api module into sys.modules
def make_playwright_modules(sync_playwright_factory):
    # top-level playwright module
    pw = ModuleType("playwright")
    # submodule with Error and TimeoutError and sync_playwright
    sync_api = ModuleType("playwright.sync_api")

    class PlaywrightError(Exception):
        pass

    class PlaywrightTimeoutError(Exception):
        pass

    sync_api.Error = PlaywrightError
    sync_api.TimeoutError = PlaywrightTimeoutError
    sync_api.sync_playwright = sync_playwright_factory

    sys.modules["playwright"] = pw
    sys.modules["playwright.sync_api"] = sync_api
    return PlaywrightError, PlaywrightTimeoutError


def test_launch_exception_round_027():
    # Simulate chromium.launch() raising an exception
    captured = {"error": None, "browser": None}

    class FakeChromium:
        def launch(self):
            raise Exception("no-browser")

    class FakePContext:
        def __init__(self):
            self.chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def sync_playwright_factory():
        return FakePContext()

    PlaywrightError, PlaywrightTimeoutError = make_playwright_modules(sync_playwright_factory)

    errors = []
    # Scraper.__init__ signature (print_error, playwright_available, verify_ssl)
    scraper = Scraper(lambda msg: errors.append(msg), True, True)
    # Ensure module variable used in function exists
    import aider.scrape as scrape_mod
    scrape_mod.aider_user_agent = "TEST_AGENT"

    content, mime = scraper.scrape_with_playwright("http://example.com")

    # Because launch failed, scraper should mark playwright unavailable and return (None, None)
    assert content is None and mime is None
    # print_error should have been called with the exception string
    assert any("no-browser" in str(e) for e in errors)


def test_timeout_and_user_agent_round_027():
    # Simulate goto raising TimeoutError, page.content succeeds, response is None
    container = {}

    class FakeBrowser:
        def __init__(self):
            self.closed = False

        def new_context(self, ignore_https_errors):
            return self

        def new_page(self):
            return container["page"]

        def close(self):
            self.closed = True

    class FakeResponse:
        def header_value(self, name):
            return None

    class FakePage:
        def __init__(self):
            self.headers = None

        def evaluate(self, expr):
            # include 'Headless' so replacement logic runs
            return "Mozilla/5.0 (Headless)"

        def set_extra_http_headers(self, headers):
            self.headers = headers

        def goto(self, url, wait_until, timeout):
            raise PlaywrightTimeoutError("timed out")

        def content(self):
            return "<html>ok</html>"

    def sync_playwright_factory():
        class Ctx:
            def __enter__(self):
                p = types.SimpleNamespace()
                # chromium.launch returns a FakeBrowser
                def launch():
                    b = FakeBrowser()
                    container["browser"] = b
                    return b

                p.chromium = types.SimpleNamespace(launch=launch)
                return p

            def __exit__(self, exc_type, exc, tb):
                return False

        return Ctx()

    PlaywrightError, PlaywrightTimeoutError = make_playwright_modules(sync_playwright_factory)

    # make PlaywrightTimeoutError visible to page methods above
    # create and register page and response
    container["page"] = FakePage()
    container["response"] = None

    errors = []
    scraper = Scraper(lambda msg: errors.append(msg), True, True)
    import aider.scrape as scrape_mod
    scrape_mod.aider_user_agent = "APPENDED"

    content, mime = scraper.scrape_with_playwright("http://example.com")

    # page.content should be returned, mime should be None because response is None
    assert content == "<html>ok</html>"
    assert mime is None
    # user agent header should have been set and include APPENDED
    header = container["page"].headers
    assert header is not None and "User-Agent" in header
    assert "APPENDED" in header["User-Agent"]
    # browser should have been closed in finally
    assert container["browser"].closed is True


def test_response_with_content_type_round_027():
    # Simulate successful goto returning response with content-type header
    container = {}

    class FakeBrowser:
        def __init__(self):
            self.closed = False

        def new_context(self, ignore_https_errors):
            return self

        def new_page(self):
            return container["page"]

        def close(self):
            self.closed = True

    class FakeResponse:
        def header_value(self, name):
            return "text/plain; charset=utf-8"

    class FakePage:
        def __init__(self):
            self.headers = None

        def evaluate(self, expr):
            return "browser"

        def set_extra_http_headers(self, headers):
            self.headers = headers

        def goto(self, url, wait_until, timeout):
            container["response"] = FakeResponse()
            return container["response"]

        def content(self):
            return "plain text"

    def sync_playwright_factory():
        class Ctx:
            def __enter__(self):
                p = types.SimpleNamespace()
                def launch():
                    b = FakeBrowser()
                    container["browser"] = b
                    return b
                p.chromium = types.SimpleNamespace(launch=launch)
                return p

            def __exit__(self, exc_type, exc, tb):
                return False

        return Ctx()

    PlaywrightError, PlaywrightTimeoutError = make_playwright_modules(sync_playwright_factory)

    container["page"] = FakePage()

    errors = []
    scraper = Scraper(lambda msg: errors.append(msg), True, True)
    import aider.scrape as scrape_mod
    scrape_mod.aider_user_agent = "UA"

    content, mime = scraper.scrape_with_playwright("http://example.com")

    assert content == "plain text"
    assert mime == "text/plain"
    assert container["browser"].closed is True


def test_content_error_round_027():
    # Simulate page.content raising PlaywrightError -> should set content and mime to None
    container = {}

    class FakeBrowser:
        def __init__(self):
            self.closed = False

        def new_context(self, ignore_https_errors):
            return self

        def new_page(self):
            return container["page"]

        def close(self):
            self.closed = True

    class FakePage:
        def evaluate(self, expr):
            return "UA"

        def set_extra_http_headers(self, headers):
            pass

        def goto(self, url, wait_until, timeout):
            # successful navigation returns a response object with no content-type
            class Resp:
                def header_value(self, name):
                    return None

            container["response"] = Resp()
            return container["response"]

        def content(self):
            raise PlaywrightError("content failed")

    def sync_playwright_factory():
        class Ctx:
            def __enter__(self):
                p = types.SimpleNamespace()
                def launch():
                    b = FakeBrowser()
                    container["browser"] = b
                    return b
                p.chromium = types.SimpleNamespace(launch=launch)
                return p

            def __exit__(self, exc_type, exc, tb):
                return False

        return Ctx()

    PlaywrightError, PlaywrightTimeoutError = make_playwright_modules(sync_playwright_factory)

    container["page"] = FakePage()

    errors = []
    scraper = Scraper(lambda msg: errors.append(msg), True, True)
    import aider.scrape as scrape_mod
    scrape_mod.aider_user_agent = "UA"

    content, mime = scraper.scrape_with_playwright("http://example.com")

    assert content is None and mime is None
    # error message should have been recorded
    assert any("content failed" in str(e) for e in errors)
    assert container["browser"].closed is True
