from browser_use.browser.watchdogs.security_watchdog import SecurityWatchdog


def test_handles_bracketed_ipv6_as_ip():
    """Direct probe: bracketed IPv6 literals (as appear in URLs) should be recognized as IP addresses.

    This test creates a SecurityWatchdog instance without running its initializer to avoid
    unrelated construction side effects and calls the private helper _is_ip_address
    with the bracketed IPv6 host '[::1]'. The independent oracle asserts the function
    returns True.
    """

    # Create a minimal instance without invoking __init__ to avoid external dependencies
    sw = object.__new__(SecurityWatchdog)

    host = '[::1]'

    # Call the method directly on the class to ensure we only exercise the target unit
    result = SecurityWatchdog._is_ip_address(sw, host)

    assert result is True, (
        "SecurityWatchdog._is_ip_address should accept URL-style bracketed IPv6 hosts (e.g. '[::1]')"
    )
