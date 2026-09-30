# file: browser_use/browser/watchdogs/downloads_watchdog.py:917-1012
# asked: {"lines": [921, 922, 923, 924, 926, 927, 931, 932, 933, 934, 935, 936, 937, 939, 940, 941, 945, 948, 949, 950, 951, 955, 958, 959, 961, 962, 964, 965, 968, 969, 970, 973, 975, 976, 977, 979, 980, 984, 985, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1012], "branches": [[948, 949], [948, 955], [961, 962], [961, 1012], [964, 961], [964, 965], [965, 961], [965, 967], [967, 965], [967, 973], [977, 979], [977, 1003], [990, 991], [990, 992], [1004, 1005], [1004, 1008]]}
# gained: {"lines": [921, 922, 923, 926, 927, 931, 932, 933, 934, 935, 936, 937, 939, 940, 941, 945, 948, 955, 958, 959, 961, 962, 964, 965, 968, 969, 970, 973, 975, 976, 977, 979, 980, 984, 985, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1003, 1004, 1005, 1008], "branches": [[948, 955], [961, 962], [964, 965], [965, 967], [967, 973], [977, 979], [990, 991], [990, 992], [1004, 1005]]}

import asyncio
from pathlib import Path

import pytest

from browser_use.browser.watchdogs.downloads_watchdog import DownloadsWatchdog
from cdp_use.cdp.browser import DownloadWillBeginEvent


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.error_msgs = []
        self.warn_msgs = []

    def debug(self, *args, **kwargs):
        self.debug_msgs.append(" ".join(map(str, args)))

    def error(self, *args, **kwargs):
        self.error_msgs.append(" ".join(map(str, args)))

    def warning(self, *args, **kwargs):
        self.warn_msgs.append(" ".join(map(str, args)))


class DummyEventBus:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class FakeLoop:
    def __init__(self):
        self._t = 0.0

    def time(self):
        return self._t


@pytest.mark.asyncio
async def test_handle_cdp_download_detects_and_dispatches(tmp_path, monkeypatch):
    # Setup temporary downloads directory and a file > 4 bytes
    downloads_dir = tmp_path
    file_path = downloads_dir / "file.txt"
    file_path.write_bytes(b"hello world")  # size > 4

    # Construct a DownloadsWatchdog instance without running its __init__
    wd = object.__new__(DownloadsWatchdog)
    # Pydantic BaseModel expects this attribute when setting fields on instances created via __new__
    wd.__pydantic_fields_set__ = set()

    # Minimal required nested objects
    class Profile:
        def __init__(self, downloads_path):
            self.downloads_path = str(downloads_path)

    class BrowserSession:
        def __init__(self, profile, id_val, is_local=True, logger=None):
            self.browser_profile = profile
            self.id = id_val
            self.is_local = is_local
            self.logger = logger

    # Assign browser_session and event_bus (fields on BaseWatchdog)
    wd.browser_session = BrowserSession(Profile(downloads_dir), id_val="session-1234", is_local=True, logger=DummyLogger())
    wd.event_bus = DummyEventBus()

    # Set internal attributes used by the handler
    wd._initial_downloads_snapshot = set()  # empty means new file will be detected
    guid = "guid-1"
    wd._cdp_downloads_info = {guid: {}}  # present so handled flag can be set
    wd._detected_downloads = set()
    wd._download_cdp_session = None

    # Fake asyncio loop and sleep to advance time deterministically
    fake_loop = FakeLoop()
    original_sleep = asyncio.sleep

    async def fake_sleep(delay):
        # advance fake time and yield control briefly using original sleep
        fake_loop._t += delay
        await original_sleep(0)

    monkeypatch.setattr(asyncio, "get_event_loop", lambda: fake_loop)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    event: DownloadWillBeginEvent = {"guid": guid, "url": "http://example.com/file.txt", "suggestedFilename": "file.txt"}

    await wd._handle_cdp_download(event, target_id="t1", session_id=None)

    # Assertions: one dispatch, and dispatched event contains expected fields
    assert len(wd.event_bus.dispatched) == 1
    dispatched = wd.event_bus.dispatched[0]
    assert getattr(dispatched, "guid", None) == guid
    assert getattr(dispatched, "url", None) == "http://example.com/file.txt"
    assert str(file_path) == getattr(dispatched, "path", None)
    assert getattr(dispatched, "file_name", None) == "file.txt"
    assert getattr(dispatched, "file_size", None) == file_path.stat().st_size
    # The download should have been marked handled for this guid
    assert wd._cdp_downloads_info[guid].get("handled") is True


@pytest.mark.asyncio
async def test_handle_cdp_download_ignored_if_already_handled(tmp_path, monkeypatch):
    # Setup temporary downloads directory and a file > 4 bytes
    downloads_dir = tmp_path
    file_path = downloads_dir / "another.bin"
    file_path.write_bytes(b"0123456789")  # size > 4

    wd = object.__new__(DownloadsWatchdog)
    wd.__pydantic_fields_set__ = set()

    class Profile:
        def __init__(self, downloads_path):
            self.downloads_path = str(downloads_path)

    class BrowserSession:
        def __init__(self, profile, id_val, is_local=True, logger=None):
            self.browser_profile = profile
            self.id = id_val
            self.is_local = is_local
            self.logger = logger

    wd.browser_session = BrowserSession(Profile(downloads_dir), id_val="session-5678", is_local=True, logger=DummyLogger())
    wd.event_bus = DummyEventBus()
    wd._initial_downloads_snapshot = set()
    guid = "handled-guid"
    # This guid is already marked handled; handler should not dispatch
    wd._cdp_downloads_info = {guid: {"handled": True}}

    wd._detected_downloads = set()
    wd._download_cdp_session = None

    fake_loop = FakeLoop()
    original_sleep = asyncio.sleep

    async def fake_sleep(delay):
        fake_loop._t += delay
        await original_sleep(0)

    monkeypatch.setattr(asyncio, "get_event_loop", lambda: fake_loop)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    event: DownloadWillBeginEvent = {"guid": guid, "url": "http://example.com/another.bin", "suggestedFilename": "another.bin"}

    await wd._handle_cdp_download(event, target_id="t2", session_id=None)

    # Since guid was already handled, no dispatch should occur
    assert len(wd.event_bus.dispatched) == 0
    # Ensure handled flag remains True
    assert wd._cdp_downloads_info[guid]["handled"] is True
