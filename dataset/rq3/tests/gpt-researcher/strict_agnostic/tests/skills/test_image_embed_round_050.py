import pytest

from gpt_researcher.skills.image_generator import ImageGenerator


def _make_gen():
    # Bypass __init__ to keep tests focused and deterministic
    return object.__new__(ImageGenerator)


def test_embed_single_image_header_round_050():
    gen = _make_gen()
    report = "Intro\n## Section A\nBody"
    images = [{"alt_text": "alt", "url": "http://example.com/img.png"}]
    suggestions = [{"section_header": "Section A"}]

    out = gen._embed_images_in_report(report, images, suggestions)

    # Image markdown must be present and placed after the matching header
    assert "![alt](http://example.com/img.png)" in out
    assert "## Section A" in out
    assert out.index("## Section A") < out.index("![alt](http://example.com/img.png)")


def test_no_image_for_non_matching_header_round_050():
    gen = _make_gen()
    report = "Intro\n## NotMatched\nBody"
    images = [{"alt_text": "alt", "url": "http://example.com/img.png"}]
    # suggestion points to a different header, so no insertion should occur
    suggestions = [{"section_header": "Other"}]

    out = gen._embed_images_in_report(report, images, suggestions)

    assert "![alt](http://example.com/img.png)" not in out
    # original header and body must be preserved
    assert "## NotMatched" in out
    assert "Body" in out


def test_header_levels_and_zip_truncation_round_050():
    gen = _make_gen()
    report = "# H1\n## H2\n### H3\n#### H4\n"

    # Two images but two suggestions as well; zip should pair them in order
    images = [
        {"alt_text": "img1", "url": "http://a/1"},
        {"alt_text": "img2", "url": "http://a/2"},
    ]
    suggestions = [
        {"section_header": "H2"},
        {"section_header": "H3"},
    ]

    out = gen._embed_images_in_report(report, images, suggestions)

    # Only headers with 2 or 3 hashes should have images inserted
    assert "![img1](http://a/1)" in out
    assert "![img2](http://a/2)" in out
    # H1 (1 hash) and H4 (4 hashes) should remain without images
    assert "# H1" in out
    assert "#### H4" in out

    # Confirm ordering: header appears before its image
    assert out.index("## H2") < out.index("![img1](http://a/1)")
    assert out.index("### H3") < out.index("![img2](http://a/2)")
