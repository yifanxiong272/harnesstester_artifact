import re
from gpt_researcher.skills.image_generator import ImageGenerator


def test_no_headers_round_050():
    """When the report has no markdown headers, the report should be unchanged.
    Covers: path where header_match is never true (no insertion branch).
    """
    report = "Line one\nAnother line"
    images = [
        {"alt_text": "unused", "url": "http://example.com/1.png"}
    ]
    suggestions = [
        {"section_header": "Some Section"}
    ]

    # Call as an unbound function; _embed_images_in_report does not use self
    result = ImageGenerator._embed_images_in_report(None, report, images, suggestions)

    # Should be identical to the input when no headers are present
    assert result == report


def test_header_without_mapping_round_050():
    """A header exists but there is no matching suggestion -> no image inserted.
    Covers: header_match True, but header_text not found in section_to_image mapping.
    """
    report = "Intro\n## Unmatched Header\nContent line"
    images = [
        {"alt_text": "foo", "url": "http://example.com/foo.png"}
    ]
    # suggestion refers to a different header name (case-sensitive), so no mapping for header in report
    suggestions = [
        {"section_header": "Different Header"}
    ]

    result = ImageGenerator._embed_images_in_report(None, report, images, suggestions)

    # The header should still be present but no image markdown should be inserted
    assert "## Unmatched Header" in result
    assert "![" not in result
    # Ensure other lines remain
    assert "Content line" in result


def test_header_with_mapping_round_050():
    """A header that matches a suggestion should have the corresponding image inserted.
    Covers: header_match True and header_text found in mapping -> image insertion branch.
    Also ensures the image markdown formatting includes the alt text and url.
    """
    report = "Top line\n## Target Section\nSome detail\nBottom"
    images = [
        {"alt_text": "TargetAlt", "url": "http://cdn.example/target.png"}
    ]
    suggestions = [
        {"section_header": "Target Section"}
    ]

    result = ImageGenerator._embed_images_in_report(None, report, images, suggestions)

    # The inserted markdown image should appear with the exact alt text and URL
    assert "![TargetAlt](http://cdn.example/target.png)" in result

    # Because the implementation inserts a blank line before and after the image markdown
    # after joining lines with '\n', we expect the header followed by a blank line then image
    assert "## Target Section\n\n![TargetAlt](http://cdn.example/target.png)" in result

    # Ensure surrounding content remains intact
    assert result.startswith("Top line")
    assert result.endswith("Bottom")
