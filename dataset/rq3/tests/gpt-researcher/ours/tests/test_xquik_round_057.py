import json
import types

import pytest

from gpt_researcher.retrievers.xquik import xquik

# We'll construct XquikSearch instances without calling its constructor
# to avoid depending on its exact __init__ signature.

class _FakeResp:
    def __init__(self, payload_bytes):
        self._payload = payload_bytes

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_instance(query="q", api_key="test-key"):
    cls = xquik.XquikSearch
    inst = object.__new__(cls)
    # set the attributes the method under test expects
    inst.query = query
    inst.api_key = api_key
    return inst


def test_search_tweets_views_and_truncate_round_057(monkeypatch):
    """
    - Provide a tweet with viewCount > 0 to exercise the branch that appends views.
    - Provide a long text (>120 chars) to exercise the truncation and '...' in the title.
    - Verify headers and URL include expected query and that returned structure matches shape.
    """
    long_text = "x" * 130
    tweet = {
        "author": {"username": "user123"},
        "text": long_text,
        "id": "98765",
        "likeCount": 10,
        "retweetCount": 2,
        "viewCount": 500,
    }
    payload = {"tweets": [tweet]}
    payload_bytes = json.dumps(payload).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=None):
        # capture the request object for later assertions
        captured['req'] = req
        return _FakeResp(payload_bytes)

    # Patch the symbol where the function under test resolves urlopen
    monkeypatch.setattr(
        "gpt_researcher.retrievers.xquik.xquik.urllib.request.urlopen",
        fake_urlopen,
    )

    inst = _make_instance(query="hello-world", api_key="APIKEY-ABC")

    results = xquik.XquikSearch._search_tweets(inst, max_results=1)

    # Basic shape
    assert isinstance(results, list)
    assert len(results) == 1

    item = results[0]

    # Title should show the username and truncated text with '...'
    assert item["title"].startswith("@user123: ")
    assert item["title"].endswith("...")
    # Ensure the truncated portion length is 120 plus the ellipsis
    assert len(item["title"]) >= len("@user123: ") + 120

    # href must be formed with username and id
    assert item["href"] == "https://x.com/user123/status/98765"

    # body must include the original text and the engagement string with views
    assert long_text in item["body"]
    assert "[10 likes, 2 RTs, 500 views]" in item["body"]

    # Inspect the captured request: URL should include the encoded query and a limit value
    req = captured.get('req')
    assert req is not None
    # The request should include the API key header
    # Depending on Python version, headers are accessible via header_items or get_header
    hdr_val = None
    try:
        hdr_val = req.get_header("X-API-Key")
    except Exception:
        # fallback to .headers dict attribute
        hdr_val = getattr(req, 'headers', {}).get('X-API-Key')
    assert hdr_val == "APIKEY-ABC"

    # Ensure the constructed URL contains the query string and limit=1
    full_url = getattr(req, 'full_url', None) or getattr(req, 'get_full_url')()
    assert "q=hello-world" in full_url
    assert "limit=1" in full_url


def test_search_tweets_no_views_unknown_user_and_limit_cap_round_057(monkeypatch):
    """
    - Provide a tweet with no author username to exercise default 'unknown'.
    - Provide viewCount == 0 to exercise the branch that does NOT append views.
    - Call with max_results > 200 to exercise the min(max_results, 200) limit behavior.
    - Also verify returned title does not truncate for short text.
    """
    short_text = "short text"
    tweet = {
        "author": {},  # missing username -> default to 'unknown'
        "text": short_text,
        "id": "abc123",
        "likeCount": 0,
        "retweetCount": 0,
        "viewCount": 0,
    }
    payload = {"tweets": [tweet]}
    payload_bytes = json.dumps(payload).encode("utf-8")

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured['req'] = req
        return _FakeResp(payload_bytes)

    monkeypatch.setattr(
        "gpt_researcher.retrievers.xquik.xquik.urllib.request.urlopen",
        fake_urlopen,
    )

    inst = _make_instance(query="qval", api_key="KEY-2")

    # Request with a large max_results should result in limit=200 in the encoded URL
    results = xquik.XquikSearch._search_tweets(inst, max_results=250)

    # One result returned and username defaulted to 'unknown'
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]

    assert item["title"] == "@unknown: short text"
    assert item["href"] == "https://x.com/unknown/status/abc123"

    # body should include engagement WITHOUT views
    assert "[0 likes, 0 RTs]" in item["body"]
    assert ", 0 views" not in item["body"]

    # Inspect captured request URL for limit cap at 200
    req = captured.get('req')
    assert req is not None
    full_url = getattr(req, 'full_url', None) or getattr(req, 'get_full_url')()
    assert "q=qval" in full_url
    # limit must be capped to 200 when max_results=250
    assert "limit=200" in full_url
