import sys
import types
import pytest
from browser_use.dom import markdown_extractor as me

@pytest.mark.asyncio
async def test_browser_session_path_round_109(monkeypatch):
    # Prepare a fake markdownify module that records kwargs and returns content
    calls = []
    fake_md_mod = types.ModuleType("markdownify")

    def fake_markdownify(page_html, **kwargs):
        # record the kwargs so we can assert keep_inline_images_in behavior
        calls.append(kwargs)
        # include a token that _preprocess_markdown_content will remove to simulate filtering
        return "convertedREMOVEcontent"

    fake_md_mod.markdownify = fake_markdownify
    # Ensure the function's internal "from markdownify import markdownify as md" imports our fake
    monkeypatch.setitem(sys.modules, "markdownify", fake_md_mod)

    # Patch HTMLSerializer used by the module to return deterministic HTML
    class FakeHTMLSerializer:
        def __init__(self, extract_links=False):
            self.extract_links = extract_links

        def serialize(self, enhanced_dom_tree):
            # include a percent-encoded sequence to ensure the re.sub branch runs
            return "<p>Test%20Text<img src='x.png' alt='a'></p>"

    monkeypatch.setattr(me, "HTMLSerializer", FakeHTMLSerializer)

    # Patch the asynchronous helper to return a deterministic enhanced DOM tree
    async def fake_get_enhanced(browser_session):
        return "DOMTREE_FROM_BROWSER"

    monkeypatch.setattr(me, "_get_enhanced_dom_tree_from_browser_session", fake_get_enhanced)

    # Patch preprocessing to remove the 'REMOVE' token and report filtered char count
    def fake_preprocess(content):
        removed = "REMOVE"
        return (content.replace(removed, ""), len(removed))

    monkeypatch.setattr(me, "_preprocess_markdown_content", fake_preprocess)

    # Fake browser session with async get_current_page_url
    class FakeBrowserSession:
        async def get_current_page_url(self):
            return "http://example.com/page"

    bs = FakeBrowserSession()

    content, stats = await me.extract_clean_markdown(
        browser_session=bs,
        dom_service=None,
        target_id=None,
        extract_links=True,
        extract_images=True,
    )

    # Assertions: content must be post-preprocess value
    assert content == "convertedcontent"

    # Stats checks: method, lengths, url included
    expected_page_html = "<p>Test%20Text<img src='x.png' alt='a'></p>"
    assert stats["method"] == "enhanced_dom_tree"
    assert stats["original_html_chars"] == len(expected_page_html)
    # initial_markdown_chars should match the markdownify raw return (before preprocess)
    assert stats["initial_markdown_chars"] == len("convertedREMOVEcontent")
    assert stats["filtered_chars_removed"] == len("REMOVE")
    assert stats["final_filtered_chars"] == len("convertedcontent")
    assert stats["url"] == "http://example.com/page"

    # Ensure markdownify was called and that keep_inline_images_in reflected extract_images=True
    assert calls, "markdownify was not called"
    last_call_kwargs = calls[-1]
    assert last_call_kwargs["keep_inline_images_in"] == [
        "td",
        "th",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ]


@pytest.mark.asyncio
async def test_dom_service_path_round_109(monkeypatch):
    # Prepare fake markdownify module to capture kwargs and simulate content
    calls = []
    fake_md_mod = types.ModuleType("markdownify")

    def fake_markdownify(page_html, **kwargs):
        calls.append(kwargs)
        return "domREMOVEmd"

    fake_md_mod.markdownify = fake_markdownify
    monkeypatch.setitem(sys.modules, "markdownify", fake_md_mod)

    # Patch HTMLSerializer to return deterministic HTML
    class FakeHTMLSerializer2:
        def __init__(self, extract_links=False):
            self.extract_links = extract_links

        def serialize(self, enhanced_dom_tree):
            return "<div>Sample%20HTML</div>"

    monkeypatch.setattr(me, "HTMLSerializer", FakeHTMLSerializer2)

    # Fake DOM service with async get_dom_tree; returns (enhanced_dom_tree, other)
    class FakeDomService:
        async def get_dom_tree(self, target_id, all_frames):
            # Validate that the function accepts the expected args; return deterministic values
            assert target_id == "target-123"
            # all_frames is intentionally passed as None per the implementation comment
            assert all_frames is None
            return ("DOMTREE_FROM_SERVICE", None)

    ds = FakeDomService()

    # Patch preprocess to remove the token and report removed chars
    monkeypatch.setattr(me, "_preprocess_markdown_content", lambda c: (c.replace("REMOVE", ""), len("REMOVE")))

    content, stats = await me.extract_clean_markdown(
        browser_session=None,
        dom_service=ds,
        target_id="target-123",
        extract_links=False,
        extract_images=False,
    )

    # After preprocess, 'domREMOVEmd' -> 'dommd'
    assert content == "dommd"

    # Stats for DOM service path
    assert stats["method"] == "dom_service"
    # No URL should be present when using dom_service path
    assert "url" not in stats

    # Ensure markdownify saw keep_inline_images_in as empty list when extract_images=False
    assert calls, "markdownify was not called"
    assert calls[-1]["keep_inline_images_in"] == []


@pytest.mark.asyncio
async def test_provide_both_browser_and_dom_raises_round_109():
    # When both browser_session and dom_service/target_id are provided, a ValueError is raised
    class DummySession:
        pass

    class DummyService:
        pass

    with pytest.raises(ValueError):
        await me.extract_clean_markdown(browser_session=DummySession(), dom_service=DummyService(), target_id="x", extract_links=False, extract_images=False)
