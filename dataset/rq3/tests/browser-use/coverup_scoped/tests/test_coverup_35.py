# file: browser_use/dom/markdown_extractor.py:22-113
# asked: {"lines": [48, 49, 50, 52, 53, 54, 55, 58, 59, 60, 62, 65, 66, 68, 71, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 90, 93, 96, 98, 101, 102, 103, 104, 105, 106, 110, 111, 113], "branches": [[48, 49], [48, 55], [49, 50], [49, 52], [55, 58], [55, 62], [110, 111], [110, 113]]}
# gained: {"lines": [48, 49, 50, 52, 53, 54, 55, 58, 59, 60, 62, 65, 66, 68, 71, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 90, 93, 96, 98, 101, 102, 103, 104, 105, 106, 110, 111, 113], "branches": [[48, 49], [48, 55], [49, 50], [49, 52], [55, 58], [55, 62], [110, 111], [110, 113]]}

import types
import sys
import pytest
import asyncio

@pytest.mark.asyncio
async def test_extract_clean_markdown_browser_session_path(monkeypatch):
    # Import the module under test
    import browser_use.dom.markdown_extractor as me

    # Prepare a fake enhanced DOM tree and page HTML
    enhanced_dom_tree = {"node": "root"}
    page_html = "<p>Hi%20there <img alt='a' src='http://img/'/></p>"

    # Monkeypatch the helper that fetches enhanced DOM tree from browser session
    async def fake_get_enhanced_dom_tree_from_browser_session(browser_session):
        # assert we receive the same fake browser session
        assert getattr(browser_session, "marker", None) == "bs"
        return enhanced_dom_tree
    monkeypatch.setattr(me, "_get_enhanced_dom_tree_from_browser_session", fake_get_enhanced_dom_tree_from_browser_session)

    # Fake browser session with async get_current_page_url
    class FakeBrowserSession:
        marker = "bs"
        async def get_current_page_url(self):
            return "http://example.test/page"

    fake_browser_session = FakeBrowserSession()

    # Replace HTMLSerializer used in module with a fake that returns our page_html
    class FakeHTMLSerializer:
        def __init__(self, extract_links=False):
            self.extract_links = extract_links
        def serialize(self, dom):
            # ensure we get the enhanced_dom_tree we expect
            assert dom is enhanced_dom_tree
            return page_html
    monkeypatch.setattr(me, "HTMLSerializer", FakeHTMLSerializer)

    # Create a fake markdownify module and function so the function's local import picks it up
    recorded_md_kwargs = {}
    def fake_markdownify(html, **kwargs):
        # record kwargs for assertions
        recorded_md_kwargs.update(kwargs)
        # return content that contains a percent-encoded sequence to trigger re.sub removal
        return "Hello%20World\n![alt](http://img/)"
    fake_md_module = types.ModuleType("markdownify")
    fake_md_module.markdownify = fake_markdownify
    monkeypatch.setitem(sys.modules, "markdownify", fake_md_module)

    # Monkeypatch _preprocess_markdown_content to return the input unchanged and 0 removed chars
    def fake_preprocess_markdown_content(content):
        # content should reflect markdownify output after percent-decoding (re.sub will remove %20)
        assert "HelloWorld" in content or "Hello" in content  # ensure re.sub ran
        return content, 0
    monkeypatch.setattr(me, "_preprocess_markdown_content", fake_preprocess_markdown_content)

    # Call the function under test with extract_images=True to trigger non-empty keep_inline_images_in
    content, stats = await me.extract_clean_markdown(browser_session=fake_browser_session, extract_images=True, extract_links=True)

    # Assertions about returned content and stats
    assert isinstance(content, str)
    # Our fake_preprocess returned the content unchanged (apart from re.sub removal), so it should contain 'HelloWorld' without '%20'
    assert "Hello%20World" not in content
    assert "HelloWorld" in content or "Hello" in content

    # Stats checks
    assert stats["method"] == "enhanced_dom_tree"
    assert stats["original_html_chars"] == len(page_html)
    # initial_markdown_chars should be the length of fake_markdownify return value
    expected_initial_len = len("Hello%20World\n![alt](http://img/)")
    assert stats["initial_markdown_chars"] == expected_initial_len
    # filtered_chars_removed is from our fake_preprocess
    assert stats["filtered_chars_removed"] == 0
    # final_filtered_chars equals length of returned content
    assert stats["final_filtered_chars"] == len(content)
    # URL should be present for browser_session path
    assert stats["url"] == "http://example.test/page"

    # Ensure markdownify was called with non-empty keep_inline_images_in when extract_images=True
    assert "keep_inline_images_in" in recorded_md_kwargs
    assert isinstance(recorded_md_kwargs["keep_inline_images_in"], list)
    assert len(recorded_md_kwargs["keep_inline_images_in"]) > 0


@pytest.mark.asyncio
async def test_extract_clean_markdown_dom_service_path_and_parameter_validation(monkeypatch):
    import browser_use.dom.markdown_extractor as me

    # Prepare fake enhanced DOM tree and page HTML for serializer
    enhanced_dom_tree = {"root": "x"}
    page_html = "<div>Test%20Content</div>"

    # Fake dom_service.get_dom_tree async method
    class FakeDomService:
        async def get_dom_tree(self, target_id, all_frames=None):
            # Validate we received the target_id from the caller
            assert target_id == "target-123"
            return enhanced_dom_tree, None
    fake_dom_service = FakeDomService()

    # Fake HTMLSerializer to return our page_html
    class FakeHTMLSerializer:
        def __init__(self, extract_links=False):
            self.extract_links = extract_links
        def serialize(self, dom):
            assert dom is enhanced_dom_tree
            return page_html
    monkeypatch.setattr(me, "HTMLSerializer", FakeHTMLSerializer)

    # Provide a markdownify module again; record kwargs to ensure keep_inline_images_in is empty when extract_images=False
    recorded_md_kwargs = {}
    def fake_markdownify(html, **kwargs):
        recorded_md_kwargs.update(kwargs)
        return "Dom%20Service%20MD\n- item"
    fake_md_module = types.ModuleType("markdownify")
    fake_md_module.markdownify = fake_markdownify
    monkeypatch.setitem(sys.modules, "markdownify", fake_md_module)

    # Preprocess removes a trailing newline and reports 1 char removed
    def fake_preprocess_markdown_content(content):
        # content should have had %20 removed by re.sub before preprocess is called
        assert "%20" not in content
        # simulate removing a newline
        new = content.rstrip("\n")
        removed = len(content) - len(new)
        return new, removed
    monkeypatch.setattr(me, "_preprocess_markdown_content", fake_preprocess_markdown_content)

    # Call the function using dom_service path with extract_images=False
    content, stats = await me.extract_clean_markdown(dom_service=fake_dom_service, target_id="target-123", extract_images=False, extract_links=False)

    # Validate results
    assert isinstance(content, str)
    assert "%20" not in content  # percent-encodings removed
    assert stats["method"] == "dom_service"
    assert "url" not in stats  # dom_service path should not include URL
    assert stats["original_html_chars"] == len(page_html)
    assert stats["initial_markdown_chars"] == len("Dom%20Service%20MD\n- item")
    # filtered chars removed should match what fake_preprocess returned
    assert stats["filtered_chars_removed"] in (0, 1)
    assert stats["final_filtered_chars"] == len(content)

    # Ensure markdownify was called with empty keep_inline_images_in when extract_images=False
    assert "keep_inline_images_in" in recorded_md_kwargs
    assert recorded_md_kwargs["keep_inline_images_in"] == []

    # Now test parameter validation: both browser_session and dom_service provided should raise ValueError
    class DummyBS:
        async def get_current_page_url(self):
            return "http://x"
    dummy_bs = DummyBS()
    with pytest.raises(ValueError) as excinfo:
        await me.extract_clean_markdown(browser_session=dummy_bs, dom_service=fake_dom_service, target_id="target-abc")
    assert "Cannot specify both browser_session and dom_service/target_id" in str(excinfo.value)

    # And neither provided should raise ValueError
    with pytest.raises(ValueError) as excinfo2:
        await me.extract_clean_markdown()
    assert "Must provide either browser_session or both dom_service and target_id" in str(excinfo2.value)
