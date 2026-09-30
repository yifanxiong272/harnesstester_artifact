# file: gpt_researcher/scraper/utils.py:16-56
# asked: {"lines": [18, 20, 22, 24, 25, 26, 27, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 47, 50, 52, 54, 55, 56], "branches": [[24, 25], [24, 50], [26, 24], [26, 27], [29, 30], [29, 32], [32, 33], [32, 47], [35, 36], [35, 47], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45]]}
# gained: {"lines": [18, 20, 22, 24, 25, 26, 27, 29, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 47, 50, 52, 54, 55, 56], "branches": [[24, 25], [24, 50], [26, 27], [29, 30], [29, 32], [32, 33], [35, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45]]}

import logging
import pytest
from bs4 import BeautifulSoup
from gpt_researcher.scraper.utils import get_relevant_images


def test_get_relevant_images_classes_and_sizes():
    html = """
    <html><body>
        <!-- class-based (should get highest score 4) -->
        <img src="images/hero.png" class="hero" />
        <!-- very large image (>=2000 x >=1000) -> score 3 -->
        <img src="images/large.png" width="2000" height="1000" />
        <!-- >=1600 width -> score 2 -->
        <img src="images/medium_large.png" width="1700" height="700" />
        <!-- >=800 width or >=500 height -> score 1 -->
        <img src="images/medium.png" width="800" height="500" />
        <!-- >=500 width or >=300 height -> score 0 -->
        <img src="images/smallish.png" width="500" height="300" />
        <!-- too small -> should be skipped -->
        <img src="images/tiny.png" width="100" height="100" />
    </body></html>
    """
    base_url = "http://example.com/path/"

    soup = BeautifulSoup(html, "html.parser")
    results = get_relevant_images(soup, base_url)

    # Ensure the tiny image was skipped
    urls = [r["url"] for r in results]
    assert all("tiny.png" not in u for u in urls)

    # Expect ordering by score descending: hero (4), large (3), medium_large (2), medium (1), smallish (0)
    expected_scores = [4, 3, 2, 1, 0]
    assert [r["score"] for r in results] == expected_scores

    # Check urls are correctly joined with base_url
    expected_urls = [
        "http://example.com/path/images/hero.png",
        "http://example.com/path/images/large.png",
        "http://example.com/path/images/medium_large.png",
        "http://example.com/path/images/medium.png",
        "http://example.com/path/images/smallish.png",
    ]
    assert urls == expected_urls


def test_get_relevant_images_limits_to_top_10_and_keeps_scores(monkeypatch):
    # Create 12 images with a class that gives score 4; ensure only first 10 are returned
    imgs = "\n".join(f'<img src="img{i}.jpg" class="thumbnail" />' for i in range(12))
    html = f"<html><body>{imgs}</body></html>"
    soup = BeautifulSoup(html, "html.parser")
    base_url = "https://site.test/dir/"

    results = get_relevant_images(soup, base_url)
    # Should return at most 10 items
    assert len(results) == 10
    # All should have score 4 (class-based)
    assert all(item["score"] == 4 for item in results)
    # Ensure the returned URLs correspond to the first 10 images
    expected_urls = [f"https://site.test/dir/img{i}.jpg" for i in range(10)]
    assert [r["url"] for r in results] == expected_urls


def test_get_relevant_images_exception_handling_and_logging(monkeypatch):
    # Create a dummy soup-like object whose find_all raises an exception
    class BrokenSoup:
        def find_all(self, *args, **kwargs):
            raise RuntimeError("boom")

    broken = BrokenSoup()

    # Capture logging.error calls
    logged = {"called": False, "msg": None}

    def fake_error(msg):
        logged["called"] = True
        logged["msg"] = msg

    monkeypatch.setattr(logging, "error", fake_error)

    result = get_relevant_images(broken, "http://irrelevant/")

    # On exception, function should return empty list and logging.error should have been called
    assert result == []
    assert logged["called"] is True
    assert "Error in get_relevant_images" in logged["msg"]
