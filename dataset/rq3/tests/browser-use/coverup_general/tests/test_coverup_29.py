# file: browser_use/dom/utils.py:8-129
# asked: {"lines": [10, 12, 13, 16, 17, 18, 20, 23, 24, 25, 26, 28, 29, 33, 34, 37, 39, 42, 43, 45, 46, 49, 51, 54, 81, 82, 83, 89, 92, 93, 94, 95, 98, 99, 101, 102, 105, 108, 109, 110, 113, 114, 116, 118, 119, 121, 125, 126, 129], "branches": [[12, 13], [12, 16], [17, 18], [17, 20], [23, 24], [23, 37], [25, 26], [25, 37], [28, 29], [28, 33], [37, 39], [37, 54], [43, 45], [43, 54], [45, 46], [45, 49], [49, 43], [49, 51], [82, 83], [82, 92], [92, 93], [92, 125], [93, 94], [93, 125], [94, 95], [94, 98], [98, 99], [98, 101], [101, 102], [101, 105], [108, 109], [108, 110], [110, 113], [110, 121], [113, 114], [113, 116], [125, 126], [125, 129]]}
# gained: {"lines": [10, 12, 13, 16, 17, 18, 20, 23, 24, 25, 26, 28, 29, 33, 34, 37, 39, 42, 43, 45, 49, 51, 54, 81, 82, 83, 89, 92, 93, 94, 95, 98, 99, 101, 102, 105, 108, 109, 110, 113, 114, 116, 118, 119, 121, 125, 126], "branches": [[12, 13], [12, 16], [17, 18], [17, 20], [23, 24], [23, 37], [25, 26], [28, 29], [28, 33], [37, 39], [43, 45], [43, 54], [45, 49], [49, 43], [49, 51], [82, 83], [92, 93], [93, 94], [93, 125], [94, 95], [94, 98], [98, 99], [98, 101], [101, 102], [101, 105], [108, 109], [108, 110], [110, 113], [110, 121], [113, 114], [113, 116], [125, 126]]}

import re
import pytest

from browser_use.dom.utils import generate_css_selector_for_element

class SimpleNode:
    def __init__(self, tag_name=None, attributes=None):
        self.tag_name = tag_name
        self.attributes = attributes or {}

def test_none_and_invalid_tag_cases():
    # None node
    assert generate_css_selector_for_element(None) is None

    # Object without tag_name attribute
    class NoTag:
        pass
    assert generate_css_selector_for_element(NoTag()) is None

    # Empty tag_name
    node_empty = SimpleNode(tag_name='')
    assert generate_css_selector_for_element(node_empty) is None

    # Invalid tag_name (starts with a digit)
    node_invalid = SimpleNode(tag_name='1div')
    assert generate_css_selector_for_element(node_invalid) is None

def test_id_handling_valid_and_special_characters():
    # Valid ID should return #id (trimmed)
    node = SimpleNode(tag_name='Div', attributes={'id': ' myID '})
    assert generate_css_selector_for_element(node) == '#myID'

    # ID with special characters (quote) should return attribute selector with escaped quote
    node_quote = SimpleNode(tag_name='span', attributes={'id': 'bad"id'})
    result = generate_css_selector_for_element(node_quote)
    assert result == 'span[id="bad\\"id"]'

    # ID with hyphen and underscore (valid per regex) should return #id
    node_validchars = SimpleNode(tag_name='a', attributes={'id': 'a_b-1'})
    assert generate_css_selector_for_element(node_validchars) == '#a_b-1'

def test_classes_and_safe_attributes_and_special_value_handling():
    attributes = {
        'class': 'btn  primary invalid@class  ',  # one invalid class (contains @) should be skipped
        'name': 'submit',
        'required': '',  # empty value should produce [required]
        'data-testid': 'some "quoted"\nmore',  # contains quote and newline -> use *= and escape quotes, newline trimmed
        'onclick': 'doSomething()',  # not in SAFE_ATTRIBUTES -> ignored
        'alt': 'alttext',
        'src': 'path/to/resource',
        # an attribute with only whitespace name should be ignored
        '': 'should_be_ignored',
    }
    node = SimpleNode(tag_name='button', attributes=attributes)

    selector = generate_css_selector_for_element(node)

    # Build expected selector piece by piece to mirror insertion order of the dict above
    expected = 'button'
    # classes: only 'btn' and 'primary' valid
    expected += '.btn.primary'
    # 'name' -> exact match
    expected += '[name="submit"]'
    # 'required' -> empty value -> [required]
    expected += '[required]'
    # 'data-testid' -> special chars: newline causes split to 'some "quoted"' then collapse/escape
    expected += '[data-testid*="some \\"quoted\\""]'
    # 'onclick' is ignored (not in SAFE_ATTRIBUTES)
    # 'alt' and 'src' should be included
    expected += '[alt="alttext"][src="path/to/resource"]'

    assert selector == expected

    # Ensure ignored attributes do not appear
    assert 'onclick' not in selector
    assert 'should_be_ignored' not in selector

def test_whitespace_and_control_characters_in_attribute_values_are_collapsed_and_escaped():
    # Title contains tabs and carriage returns which should be collapsed to spaces and used with *=
    attributes = {
        'class': 'label',
        'title': 'line1\tline2\rline3',
        'data-id': '  spaced\tvalue  ',
    }
    node = SimpleNode(tag_name='div', attributes=attributes)
    selector = generate_css_selector_for_element(node)

    # Expected: tag + .label + title (special chars -> *= with collapsed spaces) + data-id (contains whitespace -> *=)
    # Process title as function would:
    title_part = 'line1\tline2\rline3'
    # since title contains \t and \r it's processed by the "special chars" branch (no newline),
    # collapsed with \s+ -> single spaces
    collapsed_title = re.sub(r'\s+', ' ', title_part).strip()
    safe_title = collapsed_title.replace('"', '\\"')
    dataid_part = '  spaced\tvalue  '
    collapsed_dataid = re.sub(r'\s+', ' ', dataid_part).strip()
    safe_dataid = collapsed_dataid.replace('"', '\\"')

    expected = f'div.label[title*="{safe_title}"][data-id*="{safe_dataid}"]'
    assert selector == expected
