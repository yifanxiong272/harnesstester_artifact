from browser_use.browser.watchdogs.security_watchdog import SecurityWatchdog


def test_handles_bracketed_ipv6_as_ip():
    sw = object.__new__(SecurityWatchdog)
    host = '[::1]'
    result = SecurityWatchdog._is_ip_address(sw, host)
    assert result is True, (
        "SecurityWatchdog._is_ip_address should accept URL-style bracketed IPv6 hosts (e.g. '[::1]')"
    )
