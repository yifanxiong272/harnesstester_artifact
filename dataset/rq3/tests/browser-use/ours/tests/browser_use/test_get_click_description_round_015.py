import pytest
from browser_use.tools.utils import get_click_description


# Small deterministic fakes that match the shape used by get_click_description
class MockProp:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class MockAXNode:
    def __init__(self, properties=None):
        self.properties = properties or []


class MockSnapshot:
    def __init__(self, computed_styles=None):
        self.computed_styles = computed_styles or {}


class FakeNode:
    def __init__(
        self,
        tag_name,
        attributes=None,
        ax_node=None,
        children=None,
        snapshot_node=None,
        is_visible=True,
        text=''
    ):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.ax_node = ax_node
        # children should be list of FakeNode
        self.children = children or []
        self.snapshot_node = snapshot_node
        self.is_visible = is_visible
        self._text = text

    def get_all_children_text(self):
        # Return the preconfigured text, deterministic
        return self._text


def test_input_checkbox_with_empty_checked_attr_round_015():
    # input with checked attribute present as empty string -> treated as checked
    node = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox', 'checked': ''},
        ax_node=None,
        children=[],
        snapshot_node=None,
        is_visible=True,
        text=''
    )

    desc = get_click_description(node)
    # Expected exact formatting: tag, type=..., checkbox-state=checked
    assert desc == 'input type=checkbox checkbox-state=checked'


def test_input_checkbox_ax_node_override_round_015():
    # input with no checked attribute but AX node property says 'true' -> checked
    ax = MockAXNode(properties=[MockProp('checked', 'true')])
    node = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox'},
        ax_node=ax,
        children=[],
        snapshot_node=None,
        is_visible=True,
        text=''
    )

    desc = get_click_description(node)
    assert desc == 'input type=checkbox checkbox-state=checked'


def test_role_checkbox_with_ax_node_and_long_text_and_id_truncation_round_015():
    # role=checkbox with aria-checked false but AX node overrides to checked
    long_text = 'X' * 35
    ax = MockAXNode(properties=[MockProp('checked', True)])
    node = FakeNode(
        tag_name='div',
        attributes={'role': 'checkbox', 'aria-checked': 'false', 'id': 'a' * 30},
        ax_node=ax,
        children=[],
        snapshot_node=None,
        is_visible=True,
        text=long_text
    )

    desc = get_click_description(node)
    # Should include role, resolved checked state, shortened quoted text and truncated id
    assert 'role=checkbox' in desc
    assert 'checkbox-state=checked' in desc
    # Quoted shortened text should be 30 chars followed by '...'
    assert '"' + ('X' * 30) + '...' + '"' in desc
    # id should be truncated to 20 characters
    assert 'id=' + ('a' * 20) in desc
    # order sanity: tag should start the description
    assert desc.startswith('div ')


def test_label_with_hidden_child_checkbox_round_015():
    # A label containing a hidden checkbox child (opacity '0') -> checkbox-state is included
    child_ax = MockAXNode(properties=[MockProp('checked', 'true')])
    child_snapshot = MockSnapshot(computed_styles={'opacity': '0'})
    child = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox'},
        ax_node=child_ax,
        children=[],
        snapshot_node=child_snapshot,
        is_visible=True,
        text=''
    )

    parent = FakeNode(
        tag_name='label',
        attributes={},
        ax_node=None,
        children=[child],
        snapshot_node=None,
        is_visible=True,
        text=''
    )

    desc = get_click_description(parent)
    assert desc == 'label checkbox-state=checked'


def test_label_with_visible_child_no_snapshot_no_state_round_015():
    # A label with a visible checkbox child and no snapshot/computed_styles -> no checkbox-state appended
    child = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox', 'checked': ''},
        ax_node=None,
        children=[],
        snapshot_node=None,  # no computed_styles available
        is_visible=True,     # visible, so condition (is_hidden or not is_visible) is False
        text=''
    )

    parent = FakeNode(
        tag_name='label',
        attributes={},
        ax_node=None,
        children=[child],
        snapshot_node=None,
        is_visible=True,
        text=''
    )

    desc = get_click_description(parent)
    # Only the label tag should appear because the child didn't qualify as hidden nor invisible
    assert desc == 'label'
