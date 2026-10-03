def test_probe_001():
    """Probe: ensure GoogleSearch.search excludes YouTube-hosted results regardless of URL case or subdomain.

    This exercise constructs a GoogleSearch instance deterministically and patches
    requests.get and json.loads to return a controlled payload containing
    YouTube links with varying case and subdomains. The independent oracle is
    that no returned result should have a hostname that (when lowercased)
    endswith 'youtube.com'.
    """

    from unittest.mock import MagicMock, patch
    from urllib.parse import urlparse

    # Import only the public entrypoint declared in the packet
    from gpt_researcher.retrievers.google.google import GoogleSearch

    # Build instance deterministically without touching env helpers
    g = GoogleSearch.__new__(GoogleSearch)
    g.query = "q"
    g.headers = {}
    g.query_domains = None
    g.api_key = "k"
    g.cx_key = "cx"

    # Payload includes YouTube-hosted URLs with ASCII case variants and subdomains
    payload = {
        "items": [
            {"title": "YT1", "link": "https://YouTube.com/watch?v=1", "snippet": "a"},
            {"title": "YT2", "link": "https://m.YOUTUBE.com/watch?v=2", "snippet": "b"},
            {"title": "YT3", "link": "https://WWW.YouTube.COM/watch?v=3", "snippet": "c"},
            {"title": "Good", "link": "https://a.example/path", "snippet": "ok"},
        ]
    }

    # Resp object used by the target; json.loads is patched to return payload deterministically
    resp = MagicMock(status_code=200, text='{}')

    with patch("gpt_researcher.retrievers.google.google.requests.get", return_value=resp), \
         patch("gpt_researcher.retrievers.google.google.json.loads", return_value=payload):
        out = g.search(max_results=10)

    # Extract hrefs returned by the public API and compute hosts lowercased
    hrefs = [r.get("href") for r in out if isinstance(r, dict)]
    hosts = []
    for h in hrefs:
        try:
            netloc = urlparse(h).netloc
        except Exception:
            netloc = ""
        hosts.append(netloc.lower())

    # Primary oracle: no returned host should be a youtube.com host (case-insensitive, subdomains allowed)
    assert all(not host.endswith("youtube.com") for host in hosts), (
        "GoogleSearch.search returned youtube-hosted result(s) despite intended exclusion; returned hosts: %r" % hosts
    )
