# file: gpt_researcher/actions/markdown_processing.py:5-39
# asked: {"lines": [15, 16, 17, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 32, 33, 35, 37, 39], "branches": [[20, 21], [20, 39], [21, 20], [21, 22], [25, 26], [25, 28], [32, 33], [32, 35]]}
# gained: {"lines": [15, 16, 17, 19, 20, 21, 22, 23, 25, 26, 28, 29, 30, 32, 33, 35, 37, 39], "branches": [[20, 21], [20, 39], [21, 20], [21, 22], [25, 26], [25, 28], [32, 33], [32, 35]]}

import pytest
from gpt_researcher.actions.markdown_processing import extract_headers


def test_simple_headers_and_paragraphs():
    md = "# Title\nSome paragraph text.\n## Subtitle\nMore text.\n# Another Top"
    result = extract_headers(md)

    # Expect two top-level headers: "Title" and "Another Top"
    assert isinstance(result, list)
    assert len(result) == 2

    first = result[0]
    second = result[1]

    assert first["level"] == 1
    assert first["text"].strip() == "Title"
    # First should have one child, the "Subtitle"
    assert "children" in first and isinstance(first["children"], list)
    assert len(first["children"]) == 1
    child = first["children"][0]
    assert child["level"] == 2
    assert child["text"].strip() == "Subtitle"

    assert second["level"] == 1
    assert second["text"].strip() == "Another Top"


def test_hierarchy_and_pop_behavior():
    # This sequence will create a nested structure and then pop back up
    md = "# A\n## B\n### C\n## D\n# E"
    result = extract_headers(md)

    # Top-level headers should be A and E
    assert len(result) == 2
    A, E = result

    assert A["level"] == 1 and A["text"] == "A"
    assert E["level"] == 1 and E["text"] == "E"

    # A should have two children: B (which itself has child C) and D
    assert "children" in A and isinstance(A["children"], list)
    assert len(A["children"]) == 2

    B = A["children"][0]
    D = A["children"][1]

    assert B["level"] == 2 and B["text"] == "B"
    # B should have C as its child
    assert "children" in B and len(B["children"]) == 1
    C = B["children"][0]
    assert C["level"] == 3 and C["text"] == "C"

    # D should be level 2 and sibling of B
    assert D["level"] == 2 and D["text"] == "D"


def test_handles_attributes_using_monkeypatch(monkeypatch):
    # Monkeypatch markdown.markdown to return heading tags with attributes
    monkeypatch.setattr(
        "gpt_researcher.actions.markdown_processing.markdown.markdown",
        lambda text: "<h3 class='cls' id='x'>Attr Title</h3>\n<p>p</p>",
    )

    # Now call extract_headers; it should parse the header correctly despite attributes
    result = extract_headers("ignored input")

    assert isinstance(result, list)
    assert len(result) == 1
    h = result[0]
    assert h["level"] == 3
    assert h["text"] == "Attr Title"
