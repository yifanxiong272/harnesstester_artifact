import pytest
from browser_use.tools.service import _format_find_results


def test_non_dict_input_round_078():
    # Non-dict input should return an informative error string including the raw value
    data = [1, 2, 3]
    out = _format_find_results(data, "sel")
    assert out == f'find_elements returned unexpected result: {data}'


def test_no_elements_total_zero_round_078():
    # When total == 0 the function returns the 'No elements found' message
    data = {"total": 0}
    out = _format_find_results(data, ".my-selector")
    assert out == 'No elements found matching ".my-selector".'


def test_elements_truncation_attrs_and_showing_round_078():
    # Complex case: multiple elements, one with long text and attrs, showing < total
    long_text = "This    is\na    long\ttext with   irregular   whitespace " * 5
    # Ensure long_text collapses to >120 characters when whitespace collapsed
    attrs = {"id": "elem1", "class": "btn"}
    elements = [
        {
            "index": 3,
            "tag": "div",
            "text": long_text,
            "attrs": attrs,
            "children_count": 2,
        },
        # Minimal element to exercise defaults (no text, no attrs)
        {
            # intentionally omit index and tag to exercise defaults
            "children_count": 0,
        },
    ]
    data = {"elements": elements, "total": 5, "showing": 2}
    out = _format_find_results(data, "sel")

    # Header: pluralization (5 -> "elements") and selector present
    assert out.splitlines()[0] == 'Found 5 elements matching "sel":'

    # Blank line after header
    assert out.splitlines()[1] == ""

    # First element description contains index and tag
    assert "[3] <div>" in out

    # Collapsed whitespace: ensure no sequences of two spaces remain in the displayed text
    # and the displayed text is truncated with an ellipsis
    # Extract the displayed quoted text portion
    assert '"' in out
    # The long text should be collapsed and then truncated, ending with '...'
    assert '...' in out

    # Attributes should be rendered as {id="elem1", class="btn"}
    assert '{id="elem1", class="btn"}' in out

    # Children count appended
    assert '(2 children)' in out

    # Second (minimal) element should get default index/tag and (0 children)
    assert '[0] <?>' in out
    assert '(0 children)' in out

    # Because showing < total, the special showing-sentence should appear (it is appended with a leading newline)
    assert 'Showing 2 of 5 total elements. Increase max_results to see more.' in out


def test_singular_element_header_round_078():
    # When total == 1, header should use singular 'element' (no trailing 's')
    data = {"elements": [], "total": 1, "showing": 1}
    out = _format_find_results(data, "x")
    assert out.startswith('Found 1 element matching "x":')
