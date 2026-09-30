# file: gpt_researcher/skills/image_generator.py:587-629
# asked: {"lines": [603, 606, 607, 608, 611, 612, 613, 614, 615, 618, 619, 620, 621, 622, 624, 625, 627, 629], "branches": [[607, 608], [607, 611], [613, 614], [613, 629], [619, 620], [619, 627], [621, 622], [621, 627]]}
# gained: {"lines": [603, 606, 607, 608, 611, 612, 613, 614, 615, 618, 619, 620, 621, 622, 624, 625, 627, 629], "branches": [[607, 608], [607, 611], [613, 614], [613, 629], [619, 620], [619, 627], [621, 622], [621, 627]]}

import pytest
from gpt_researcher.skills.image_generator import ImageGenerator

class DummyCfg:
    image_generation_max_images = 3

class DummyResearcher:
    def __init__(self):
        self.cfg = DummyCfg()

def setup_generator(monkeypatch):
    # Prevent any provider initialization side-effects during __init__
    monkeypatch.setattr(ImageGenerator, "_init_provider", lambda self: None)
    return ImageGenerator(DummyResearcher())

def test_embed_single_image_after_header(monkeypatch):
    gen = setup_generator(monkeypatch)
    report = "Intro\n## Section A\nContent A"
    images = [{"alt_text": "A image", "url": "http://a"}]
    suggestions = [{"section_header": "Section A"}]

    result = gen._embed_images_in_report(report, images, suggestions)

    expected = "Intro\n## Section A\n\n![A image](http://a)\n\nContent A"
    assert result == expected
    assert "## Section A" in result
    assert "![A image](http://a)" in result
    assert "## Section A\n\n!" in result

def test_embed_multiple_images_and_ignore_nonmatching_headers(monkeypatch):
    gen = setup_generator(monkeypatch)
    report_lines = [
        "Start",
        "## A",
        "Paragraph",
        "### B",
        "Later",
        "## C",
        "End",
    ]
    report = "\n".join(report_lines)

    images = [
        {"alt_text": "imgA", "url": "http://a"},
        {"alt_text": "imgB", "url": "http://b"},
    ]
    suggestions = [
        {"section_header": "A"},
        {"section_header": "B"},
    ]

    result = gen._embed_images_in_report(report, images, suggestions)

    expected = (
        "Start\n"
        "## A\n\n![imgA](http://a)\n\n"
        "Paragraph\n"
        "### B\n\n![imgB](http://b)\n\n"
        "Later\n"
        "## C\n"
        "End"
    )
    assert result == expected

    assert "## A" in result and "![imgA](http://a)" in result
    assert "### B" in result and "![imgB](http://b)" in result
    # Ensure section C did not get an image inserted
    assert "## C\n\n![" not in result
