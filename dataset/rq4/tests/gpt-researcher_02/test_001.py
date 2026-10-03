from types import SimpleNamespace

from gpt_researcher.actions.retriever import get_retrievers


def _cfg():
    """Return a minimal cfg-like object with the attributes used by get_retrievers."""
    return SimpleNamespace(retrievers=None, retriever=None)


def test_probe_001():
    """Probe: when headers['retrievers'] contains only commas/whitespace, the
    function should fall back to the default retriever rather than returning
    an empty list.

    This test constructs a deterministic header value that is truthy but
    yields no valid names after splitting/stripping (e.g. ' ,  , '). The
    conservative public invariant asserted here (derived from retrieved
    context) is that callers must receive at least the default retriever
    class; the default's class name is expected to be 'TavilySearch'.
    """
    headers = {"retrievers": " ,  , "}
    cfg = _cfg()

    result = get_retrievers(headers, cfg)

    # Primary oracle: result must be a non-empty list and must contain the
    # default retriever class as its first element (default class name
    # observed from retrieved context: 'TavilySearch').
    assert isinstance(result, list), f"Expected list result, got {type(result)!r}"
    assert len(result) >= 1, "Expected at least one retriever (fallback to default), got empty list"

    first = result[0]
    # Use the class __name__ to avoid importing additional symbols; the
    # retrieved context documents that the default retriever is TavilySearch.
    assert getattr(first, "__name__", None) == "TavilySearch", (
        f"Expected default retriever 'TavilySearch' as first result, got {first!r}"
    )
