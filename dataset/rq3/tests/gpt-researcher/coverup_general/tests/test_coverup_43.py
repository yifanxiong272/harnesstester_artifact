# file: gpt_researcher/skills/image_generator.py:587-629
# asked: {"lines": [603, 606, 607, 608, 611, 612, 613, 614, 615, 618, 619, 620, 621, 622, 624, 625, 627, 629], "branches": [[607, 608], [607, 611], [613, 614], [613, 629], [619, 620], [619, 627], [621, 622], [621, 627]]}
# gained: {"lines": [603, 606, 607, 608, 611, 612, 613, 614, 615, 618, 619, 620, 621, 622, 624, 625, 627, 629], "branches": [[607, 608], [607, 611], [613, 614], [613, 629], [619, 620], [619, 627], [621, 622], [621, 627]]}

import pytest

from gpt_researcher.skills import image_generator as ig_module
from gpt_researcher.skills.image_generator import ImageGenerator


class DummyCfg:
    def __init__(self):
        self.image_generation_max_images = 3


class DummyResearcher:
    def __init__(self):
        self.cfg = DummyCfg()


@pytest.fixture(autouse=True)
def noop_init_provider(monkeypatch):
    # Prevent any real provider initialization during tests
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)
    yield


def test_embed_images_inserts_after_2_and_3_hash_headers():
    researcher = DummyResearcher()
    gen = ImageGenerator(researcher)

    report = "\n".join(
        [
            "Introduction line",
            "## Header One",
            "Some paragraph under header one.",
            "### Header Two",
            "More text under header two.",
            "Conclusion",
        ]
    )

    images = [
        {"alt_text": "AltOne", "url": "http://example.com/one.png"},
        {"alt_text": "AltTwo", "url": "http://example.com/two.png"},
    ]
    suggestions = [
        {"section_header": "Header One"},
        {"section_header": "Header Two"},
    ]

    result = gen._embed_images_in_report(report, images, suggestions)

    # Both images should be embedded somewhere in the result
    assert "![AltOne](http://example.com/one.png)" in result
    assert "![AltTwo](http://example.com/two.png)" in result

    # Image for Header One must come after its header
    assert result.find("## Header One") < result.find("![AltOne](http://example.com/one.png)")

    # Image for Header Two must come after its header
    assert result.find("### Header Two") < result.find("![AltTwo](http://example.com/two.png)")

    # Ensure original non-header lines remain
    assert "Some paragraph under header one." in result
    assert "More text under header two." in result


def test_embed_images_handles_single_hash_and_zip_truncation_and_exact_match():
    researcher = DummyResearcher()
    gen = ImageGenerator(researcher)

    # Create report with a single-hash header (should NOT match),
    # and two 2-hash headers (only one will be paired via zip)
    report_lines = [
        "# Single",         # single-hash -> should not match regex
        "## Paired",        # should match and get image
        "Content paired",
        "## Unpaired",      # should match but not receive image because of zip truncation
        "Content unpaired",
    ]
    report = "\n".join(report_lines)

    # images/suggestions: first pairs to "Single" (but header is single-hash so won't be embedded),
    # second pairs to "Paired" and should be embedded. No image for "Unpaired".
    images = [
        {"alt_text": "SingleAlt", "url": "http://example.com/single.png"},
        {"alt_text": "PairedAlt", "url": "http://example.com/paired.png"},
    ]
    suggestions = [
        {"section_header": "Single"},
        {"section_header": "Paired"},
    ]

    result = gen._embed_images_in_report(report, images, suggestions)

    # The 'Paired' image must be embedded
    assert "![PairedAlt](http://example.com/paired.png)" in result
    assert result.find("## Paired") < result.find("![PairedAlt](http://example.com/paired.png)")

    # The 'Single' image should NOT be embedded because header uses a single '#'
    assert "![SingleAlt](http://example.com/single.png)" not in result

    # There should be no image for 'Unpaired' because it had no corresponding image in the zipped pairs
    assert "Unpaired" in result  # header still present
    # Ensure no unrelated image markdown appears
    assert "http://example.com/unpaired.png" not in result
