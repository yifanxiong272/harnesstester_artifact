# file: browser_use/cli.py:1728-1987
# asked: {"lines": [1728, 1730, 1731, 1733, 1735, 1736, 1739, 1741, 1743, 1744, 1745, 1746, 1747, 1748, 1749, 1752, 1753, 1754, 1755, 1758, 1759, 1760, 1762, 1763, 1764, 1767, 1768, 1770, 1772, 1774, 1780, 1783, 1784, 1787, 1788, 1789, 1790, 1793, 1794, 1795, 1796, 1797, 1798, 1799, 1800, 1801, 1802, 1803, 1804, 1805, 1806, 1807, 1809, 1810, 1811, 1812, 1815, 1818, 1821, 1822, 1823, 1824, 1825, 1826, 1827, 1828, 1829, 1830, 1831, 1833, 1836, 1839, 1840, 1841, 1843, 1844, 1845, 1846, 1847, 1848, 1851, 1852, 1853, 1854, 1855, 1856, 1857, 1858, 1859, 1862, 1863, 1865, 1866, 1868, 1869, 1873, 1874, 1876, 1877, 1879, 1880, 1881, 1884, 1885, 1886, 1887, 1889, 1890, 1891, 1893, 1895, 1896, 1897, 1898, 1899, 1901, 1902, 1904, 1907, 1909, 1910, 1911, 1912, 1913, 1914, 1915, 1916, 1917, 1918, 1920, 1921, 1922, 1926, 1927, 1928, 1929, 1930, 1932, 1933, 1936, 1939, 1940, 1941, 1942, 1943, 1944, 1945, 1946, 1948, 1950, 1951, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1963, 1965, 1966, 1968, 1969, 1971, 1972, 1973, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1984, 1985, 1986, 1987], "branches": [[1747, 1748], [1747, 1749], [1752, 1753], [1752, 1762], [1852, 0], [1852, 1853], [1857, 1852], [1857, 1858], [1889, 1890], [1889, 1895], [1904, 1907], [1904, 1954], [1971, 1972], [1971, 1987]]}
# gained: {"lines": [1728, 1730, 1731, 1733, 1735, 1736, 1739, 1741, 1743, 1744, 1745, 1746, 1747, 1748, 1749, 1752, 1753, 1754, 1755, 1758, 1759, 1760, 1762, 1763, 1764, 1767, 1768, 1770, 1772, 1774, 1780, 1783, 1784, 1787, 1788, 1789, 1790, 1793, 1794, 1795, 1796, 1797, 1798, 1799, 1800, 1801, 1802, 1803, 1804, 1805, 1806, 1807, 1809, 1810, 1811, 1812, 1815, 1818, 1821, 1822, 1823, 1824, 1825, 1826, 1827, 1828, 1829, 1830, 1831, 1833, 1836, 1839, 1840, 1841, 1843, 1844, 1845, 1846, 1847, 1848, 1851, 1852, 1853, 1854, 1855, 1856, 1857, 1858, 1859, 1862, 1863, 1865, 1866, 1868, 1869, 1873, 1874, 1876, 1877, 1879, 1880, 1881, 1884, 1885, 1886, 1887, 1889, 1890, 1891, 1893, 1904, 1907, 1909, 1910, 1911, 1912, 1913, 1914, 1915, 1916, 1917, 1918, 1920, 1921, 1922, 1926, 1927, 1928, 1929, 1930, 1932, 1933, 1936, 1939, 1940, 1941, 1942, 1943, 1944, 1945, 1946, 1948, 1950, 1951, 1968, 1969, 1971, 1972, 1973, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1984, 1985, 1986, 1987], "branches": [[1747, 1748], [1747, 1749], [1752, 1753], [1752, 1762], [1852, 1853], [1857, 1852], [1857, 1858], [1889, 1890], [1904, 1907], [1971, 1972]]}

import asyncio
import types
import sys
import builtins
import pytest

from importlib import import_module

# Import the function to test
from browser_use.cli import run_auth_command


@pytest.mark.asyncio
async def test_run_auth_command_already_authenticated(monkeypatch, tmp_path):
    """
    If the DeviceAuthClient reports is_authenticated True, the function should
    print status and return early without creating CloudSync or raising.
    """

    class FakeAuthConfig:
        def __init__(self):
            self.authorized_at = "2026-01-01T00:00:00Z"

    class FakeDeviceAuthClient:
        def __init__(self, *args, **kwargs):
            self.api_token = "token"
            self.user_id = "user1"
            self.temp_user_id = "temp1"
            self.device_id = "dev1"
            self.is_authenticated = True
            self.auth_config = FakeAuthConfig()
            self.base_url = "https://api.example.com"

    # Patch the DeviceAuthClient used in run_auth_command
    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", FakeDeviceAuthClient)

    # Ensure CloudSync is not accidentally constructed; make a CloudSync that would fail if used
    def bogus_cloudsync(*args, **kwargs):
        raise RuntimeError("CloudSync should not be constructed for already-authenticated clients")

    monkeypatch.setattr("browser_use.sync.service.CloudSync", bogus_cloudsync)

    # Run the function; it should return normally (None)
    result = await run_auth_command()
    assert result is None
    # Ensure the environment variable was set during the function
    assert "BROWSER_USE_CLOUD_SYNC" in __import__("os").environ
    assert __import__("os").environ["BROWSER_USE_CLOUD_SYNC"] == "true"


@pytest.mark.asyncio
async def test_run_auth_command_success_flow(monkeypatch):
    """
    Simulate a successful authentication flow where CloudSync.authenticate completes
    successfully, and the sync_service handles session, task, step and completion events.
    """

    # Save original asyncio.sleep to speed tests
    orig_sleep = asyncio.sleep

    async def fast_sleep(_):
        # very short real sleep to yield control
        await orig_sleep(0.001)

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    # Fake DeviceAuthClient: always not authenticated for original and fresh instances
    class FakeAuthConfig:
        def __init__(self):
            self.authorized_at = None

    class FakeDeviceAuthClient:
        def __init__(self, *args, **kwargs):
            self.api_token = None
            self.user_id = "userX"
            self.temp_user_id = "tempX"
            self.device_id = "devX"
            self.is_authenticated = False
            self.auth_config = FakeAuthConfig()
            self.base_url = "https://api.example.com"

    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", FakeDeviceAuthClient)

    # Fake uuid7str returning unique values
    uid_counter = {"n": 0}

    def uuid7str():
        uid_counter["n"] += 1
        return f"uuid-{uid_counter['n']}"

    monkeypatch.setattr("uuid_extensions.uuid7str", uuid7str)

    # Fake CloudSync that records handled events and provides an authenticate coroutine
    class FakeCloudSync:
        def __init__(self, allow_session_events_for_auth=False):
            self.allow_session_events_for_auth = allow_session_events_for_auth
            self.auth_flow_active = False
            self.session_id = None
            self.auth_client = None
            self.events = []

        def set_auth_flow_active(self):
            self.auth_flow_active = True

        async def handle_event(self, event):
            # record events for assertions
            self.events.append(event)
            # no-op

        async def authenticate(self, show_instructions=True):
            # quickly simulate success
            await fast_sleep(0)
            return True

    monkeypatch.setattr("browser_use.sync.service.CloudSync", FakeCloudSync)

    # create_task_with_error_handling should return an asyncio.Task so that .cancel() exists
    def create_task_with_error_handling(coro, name=None, suppress_exceptions=False):
        return asyncio.create_task(coro)

    monkeypatch.setattr("browser_use.utils.create_task_with_error_handling", create_task_with_error_handling)

    # Minimal event classes accepted by handle_event; they can just be dict-like or simple objects.
    # The code only constructs them and passes to handle_event; we don't need special behavior.
    def make_event_class(name):
        def ctor(**kwargs):
            obj = types.SimpleNamespace(__event_name__=name, data=kwargs)
            return obj
        return ctor

    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentSessionEvent", make_event_class("CreateAgentSessionEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentTaskEvent", make_event_class("CreateAgentTaskEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentStepEvent", make_event_class("CreateAgentStepEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.UpdateAgentTaskEvent", make_event_class("UpdateAgentTaskEvent"))

    # Now run the command
    await run_auth_command()

    # After run, ensure CloudSync recorded at least session, task, step, completion events.
    # We can get the last constructed CloudSync instance by instantiating a dummy and reusing module attr isn't available.
    # Instead, monkeypatch CloudSync to store last instance in outer scope.
    # To do that, re-run with modified CloudSync that captures the instance.
    instances = []

    class CapturingCloudSync(FakeCloudSync):
        def __init__(self, allow_session_events_for_auth=False):
            super().__init__(allow_session_events_for_auth=allow_session_events_for_auth)
            instances.append(self)

    monkeypatch.setattr("browser_use.sync.service.CloudSync", CapturingCloudSync)

    # Run again to capture events
    await run_auth_command()

    assert instances, "CloudSync instance was not created"
    inst = instances[-1]
    # There should be at least 4 events: session, task, step, completion
    assert len(inst.events) >= 4
    # Check that the first event looks like a session event
    assert getattr(inst.events[0], "__event_name__", "") == "CreateAgentSessionEvent"
    # Check that we have a CreateAgentTaskEvent somewhere
    assert any(getattr(ev, "__event_name__", "") == "CreateAgentTaskEvent" for ev in inst.events)
    assert any(getattr(ev, "__event_name__", "") == "CreateAgentStepEvent" for ev in inst.events)
    assert any(getattr(ev, "__event_name__", "") == "UpdateAgentTaskEvent" for ev in inst.events)


@pytest.mark.asyncio
async def test_run_auth_command_timeout_then_background_success(monkeypatch):
    """
    Simulate authenticate raising TimeoutError so the TimeoutError branch runs.
    Then ensure fresh DeviceAuthClient reports authenticated, leading to success branch.
    """

    orig_sleep = asyncio.sleep

    async def fast_sleep(_):
        await orig_sleep(0.001)

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    # DeviceAuthClient behavior: first instance is original (not authenticated), second (fresh) is authenticated
    class FakeAuthConfig:
        def __init__(self):
            self.authorized_at = None

    class FakeDeviceAuthClient:
        inst_count = 0

        def __init__(self, *args, **kwargs):
            FakeDeviceAuthClient.inst_count += 1
            self.api_token = None
            self.user_id = f"user{FakeDeviceAuthClient.inst_count}"
            self.temp_user_id = f"temp{FakeDeviceAuthClient.inst_count}"
            self.device_id = f"dev{FakeDeviceAuthClient.inst_count}"
            # First instance: not authenticated. Later instances (fresh checks) will report authenticated.
            self.is_authenticated = False if FakeDeviceAuthClient.inst_count == 1 else True
            self.auth_config = FakeAuthConfig()
            self.base_url = "https://api.example.com"

    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", FakeDeviceAuthClient)

    # uuid7str simple
    def uuid7str():
        return "uid-timeout"

    monkeypatch.setattr("uuid_extensions.uuid7str", uuid7str)

    # CloudSync that raises TimeoutError from authenticate
    class TimeoutCloudSync:
        def __init__(self, allow_session_events_for_auth=False):
            self.allow_session_events_for_auth = allow_session_events_for_auth
            self.session_id = None
            self.auth_client = None
            self.events = []

        def set_auth_flow_active(self):
            pass

        async def handle_event(self, event):
            self.events.append(event)

        async def authenticate(self, show_instructions=True):
            # Raise TimeoutError to trigger the except TimeoutError branch
            raise TimeoutError("simulated timeout")

    monkeypatch.setattr("browser_use.sync.service.CloudSync", TimeoutCloudSync)

    # create_task wrapper
    def create_task_with_error_handling(coro, name=None, suppress_exceptions=False):
        return asyncio.create_task(coro)

    monkeypatch.setattr("browser_use.utils.create_task_with_error_handling", create_task_with_error_handling)

    # Event constructors
    def make_event_class(name):
        def ctor(**kwargs):
            return types.SimpleNamespace(__event_name__=name, data=kwargs)
        return ctor

    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentSessionEvent", make_event_class("CreateAgentSessionEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentTaskEvent", make_event_class("CreateAgentTaskEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentStepEvent", make_event_class("CreateAgentStepEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.UpdateAgentTaskEvent", make_event_class("UpdateAgentTaskEvent"))

    # Run the command: should not raise, and should proceed down TimeoutError branch where fresh client is authenticated
    await run_auth_command()

    # Ensure that second instantiation of DeviceAuthClient happened (fresh check)
    assert FakeDeviceAuthClient.inst_count >= 2


@pytest.mark.asyncio
async def test_run_auth_command_outer_exception_triggers_exit(monkeypatch):
    """
    Simulate an exception deep in the try block so the outer exception handler executes
    and sys.exit(1) is called. We monkeypatch sys.exit to raise SystemExit so it can be caught.
    """

    # DeviceAuthClient standard fake (not authenticated)
    class FakeAuthConfig:
        def __init__(self):
            self.authorized_at = None

    class FakeDeviceAuthClient:
        def __init__(self, *args, **kwargs):
            self.api_token = None
            self.user_id = "u"
            self.temp_user_id = "t"
            self.device_id = "d"
            self.is_authenticated = False
            self.auth_config = FakeAuthConfig()
            self.base_url = "https://api.example.com"

    monkeypatch.setattr("browser_use.sync.auth.DeviceAuthClient", FakeDeviceAuthClient)
    monkeypatch.setattr("uuid_extensions.uuid7str", lambda: "uid-exc")

    # CloudSync whose handle_event raises an exception on first call
    class ExplodingCloudSync:
        def __init__(self, allow_session_events_for_auth=False):
            self.allow_session_events_for_auth = allow_session_events_for_auth
            self.session_id = None
            self.auth_client = None

        def set_auth_flow_active(self):
            pass

        async def handle_event(self, event):
            raise RuntimeError("boom in handle_event")

        async def authenticate(self, show_instructions=True):
            return True

    monkeypatch.setattr("browser_use.sync.service.CloudSync", ExplodingCloudSync)

    # Event constructors
    def make_event_class(name):
        def ctor(**kwargs):
            return types.SimpleNamespace(__event_name__=name, data=kwargs)
        return ctor

    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentSessionEvent", make_event_class("CreateAgentSessionEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentTaskEvent", make_event_class("CreateAgentTaskEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.CreateAgentStepEvent", make_event_class("CreateAgentStepEvent"))
    monkeypatch.setattr("browser_use.agent.cloud_events.UpdateAgentTaskEvent", make_event_class("UpdateAgentTaskEvent"))

    # Monkeypatch sys.exit to raise SystemExit so we can assert it was called
    def fake_exit(code=0):
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", fake_exit)

    # Run and assert SystemExit is raised with code 1
    with pytest.raises(SystemExit) as excinfo:
        await run_auth_command()
    assert excinfo.value.code == 1
