import gpt_researcher.master.actions as actions
from gpt_researcher.master.actions import extract_headers


def test_probe_001(monkeypatch):
    """
    Patch the markdown renderer to return a malformed header tag '<h>Bad</h>' followed by a valid '<h1>Good</h1>'.
    The extractor should skip the malformed tag and return only the valid header instead of raising.
    """
    # Patch actions.markdown.markdown to a deterministic function returning targeted HTML
    monkeypatch.setattr(actions.markdown, "markdown", lambda text: "<h>Bad</h>\n<h1>Good</h1>")

    # Call the targeted entrypoint
    result = extract_headers("irrelevant")

    # Primary behavioral oracle: should extract only the well-formed header and not raise
    assert result == [{"level": 1, "text": "Good"}]
