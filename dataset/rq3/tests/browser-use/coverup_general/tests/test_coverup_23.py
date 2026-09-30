# file: browser_use/tools/utils.py:6-82
# asked: {"lines": [8, 11, 14, 15, 16, 19, 20, 22, 23, 24, 25, 26, 27, 28, 31, 32, 33, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 50, 51, 53, 54, 55, 56, 57, 59, 61, 62, 63, 64, 65, 66, 67, 68, 69, 72, 73, 74, 75, 78, 79, 80, 82], "branches": [[14, 15], [14, 31], [19, 20], [19, 31], [22, 23], [22, 27], [23, 24], [23, 27], [24, 23], [24, 25], [31, 32], [31, 48], [36, 37], [36, 48], [39, 40], [39, 44], [40, 41], [40, 44], [41, 40], [41, 42], [48, 50], [48, 72], [50, 51], [50, 72], [51, 50], [51, 53], [54, 55], [54, 59], [56, 57], [56, 59], [59, 50], [59, 61], [62, 63], [62, 67], [63, 64], [63, 67], [64, 63], [64, 65], [73, 74], [73, 78], [78, 79], [78, 82], [79, 78], [79, 80]]}
# gained: {"lines": [8, 11, 14, 15, 16, 19, 20, 22, 23, 24, 25, 26, 27, 28, 31, 32, 33, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 50, 51, 53, 54, 55, 56, 57, 59, 61, 62, 63, 64, 65, 66, 67, 68, 69, 72, 73, 74, 75, 78, 79, 80, 82], "branches": [[14, 15], [14, 31], [19, 20], [22, 23], [23, 24], [24, 25], [31, 32], [31, 48], [36, 37], [39, 40], [40, 41], [41, 42], [48, 50], [48, 72], [50, 51], [50, 72], [51, 53], [54, 55], [54, 59], [56, 57], [59, 61], [62, 63], [62, 67], [63, 64], [64, 65], [73, 74], [73, 78], [78, 79], [78, 82], [79, 78], [79, 80]]}

import pytest
from types import SimpleNamespace

from browser_use.tools.utils import get_click_description


class FakeProp:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class FakeAXNode:
    def __init__(self, properties=None):
        self.properties = properties or []


class FakeSnapshotNode:
    def __init__(self, computed_styles=None):
        self.computed_styles = computed_styles or {}


class FakeNode:
    def __init__(
        self,
        tag_name,
        attributes=None,
        ax_node=None,
        snapshot_node=None,
        is_visible=True,
        children=None,
        text="",
    ):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.ax_node = ax_node
        self.snapshot_node = snapshot_node
        self.is_visible = is_visible
        self.children = children or []
        self._text = text

    def get_all_children_text(self):
        return self._text


def test_input_checkbox_ax_property_overrides_and_id_truncation():
    # Input checkbox with checked='false' in attributes, but AX node says checked True
    long_id = "myid12345678901234567890EXTRA"
    node = FakeNode(
        tag_name="input",
        attributes={"type": "checkbox", "checked": "false", "id": long_id},
        ax_node=FakeAXNode([FakeProp("checked", True)]),
        snapshot_node=None,
        is_visible=True,
        children=[],
        text="short text",
    )

    desc = get_click_description(node)
    # Basic components
    assert "input" in desc
    assert "type=checkbox" in desc
    # AX prop should override attribute to checked
    assert "checkbox-state=checked" in desc
    # Text should appear quoted
    assert '"short text"' in desc
    # id should be truncated to 20 chars
    assert f"id={long_id[:20]}" in desc
    # Full description should contain parts separated by spaces
    parts = desc.split()
    assert parts[0] == "input"


def test_role_checkbox_with_ax_property_and_name_truncation():
    # role=checkbox with aria-checked false overridden by AX property
    long_name = "n" * 30
    node = FakeNode(
        tag_name="div",
        attributes={"role": "checkbox", "aria-checked": "false", "name": long_name},
        ax_node=FakeAXNode([FakeProp("checked", "true")]),
        snapshot_node=None,
        is_visible=True,
        children=[],
        text="",
    )

    desc = get_click_description(node)
    # role present
    assert "role=checkbox" in desc
    # AX prop should mark checkbox as checked
    assert "checkbox-state=checked" in desc
    # name should be truncated to 20 chars
    assert f"name={long_name[:20]}" in desc
    # No text should be present
    assert '"' not in desc


def test_label_with_hidden_child_checkbox_and_text_truncation():
    # Parent label with hidden child input (opacity '0') that is checked via attribute
    child = FakeNode(
        tag_name="input",
        attributes={"type": "checkbox", "checked": "checked"},
        ax_node=None,
        snapshot_node=FakeSnapshotNode({"opacity": "0"}),
        is_visible=True,
        children=[],
        text="",
    )
    long_text = "x" * 40  # >30 to force ellipsis
    parent = FakeNode(
        tag_name="label",
        attributes={},
        ax_node=None,
        snapshot_node=None,
        is_visible=True,
        children=[child],
        text=long_text,
    )

    desc = get_click_description(parent)
    # Tag name present
    assert desc.startswith("label")
    # Hidden child's checkbox state should be detected as checked
    assert "checkbox-state=checked" in desc
    # Text should be truncated to 30 characters + '...'
    expected_short = '"' + (long_text[:30] + "...") + '"'
    assert expected_short in desc


def test_div_with_invisible_child_checkbox_unchecked_by_ax_property():
    # Parent div with a child input checkbox that is invisible (is_visible=False)
    # AX property explicitly false -> results in unchecked
    child = FakeNode(
        tag_name="input",
        attributes={"type": "checkbox"},
        ax_node=FakeAXNode([FakeProp("checked", False)]),
        snapshot_node=None,
        is_visible=False,
        children=[],
        text="",
    )
    parent = FakeNode(
        tag_name="div",
        attributes={},
        ax_node=None,
        snapshot_node=None,
        is_visible=True,
        children=[child],
        text="",
    )

    desc = get_click_description(parent)
    assert desc.startswith("div")
    # Invisible child should be considered and result in unchecked
    assert "checkbox-state=unchecked" in desc
