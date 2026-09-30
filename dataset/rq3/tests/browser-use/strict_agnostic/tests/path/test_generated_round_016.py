import types
from browser_use.tools.utils import get_click_description


class _FakeAXProp:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class _FakeAXNode:
    def __init__(self, properties=None):
        self.properties = properties or []


class _FakeSnapshot:
    def __init__(self, computed_styles=None):
        self.computed_styles = computed_styles or {}


class FakeNode:
    def __init__(self,
                 tag_name='div',
                 attributes=None,
                 ax_node=None,
                 snapshot_node=None,
                 is_visible=True,
                 children=None,
                 text=''):
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.ax_node = ax_node
        self.snapshot_node = snapshot_node
        self.is_visible = is_visible
        self.children = children or []
        self._text = text

    def get_all_children_text(self):
        # Simulate aggregation of children's text; deterministic
        return self._text


def test_input_checkbox_checked_round_016():
    # input explicitly checked via attributes -> checkbox-state=checked
    node = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox', 'checked': 'true'},
        ax_node=None,
    )
    desc = get_click_description(node)
    # Expect exact ordering: tag_name, type=..., checkbox-state=...
    assert desc == 'input type=checkbox checkbox-state=checked'


def test_input_checkbox_checked_via_ax_property_round_016():
    # input without checked attribute but AX node signals checked
    ax = _FakeAXNode(properties=[_FakeAXProp('checked', 'true')])
    node = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox'},
        ax_node=ax,
    )
    desc = get_click_description(node)
    # Should show checked driven by AX property
    assert 'type=checkbox' in desc
    assert 'checkbox-state=checked' in desc
    # Ensure starts with tag name
    assert desc.startswith('input ')


def test_role_checkbox_unchecked_with_ax_false_round_016():
    # role=checkbox branch; aria-checked false and AX prop false -> unchecked
    ax = _FakeAXNode(properties=[_FakeAXProp('checked', False)])
    node = FakeNode(
        tag_name='div',
        attributes={'role': 'checkbox', 'aria-checked': 'false'},
        ax_node=ax,
    )
    desc = get_click_description(node)
    # Should include role and checkbox-state=unchecked
    assert 'role=checkbox' in desc
    assert 'checkbox-state=unchecked' in desc
    # role token should appear after tag name
    assert desc.split()[0] == 'div'


def test_hidden_child_checkbox_detected_round_016():
    # Parent label/span/div with a hidden child checkbox -> state added
    # Child lacks visible attribute and has opacity 0 in snapshot
    child_snapshot = _FakeSnapshot(computed_styles={'opacity': '0'})
    child_ax = _FakeAXNode(properties=[_FakeAXProp('checked', True)])
    child = FakeNode(
        tag_name='input',
        attributes={'type': 'checkbox'},
        snapshot_node=child_snapshot,
        ax_node=child_ax,
        is_visible=True,  # visibility alone does not prevent hidden if opacity 0
    )
    parent = FakeNode(
        tag_name='label',
        attributes={},
        children=[child],
    )
    desc = get_click_description(parent)
    # Should include checkbox-state derived from the hidden child AX property
    assert desc.startswith('label')
    assert 'checkbox-state=checked' in desc


def test_text_truncation_and_key_attributes_round_016():
    # Long text should be truncated to 30 chars + '...'
    long_text = 'x' * 40
    node = FakeNode(
        tag_name='p',
        attributes={'id': 'my-very-long-id-which-will-be-truncated', 'name': 'n', 'aria-label': 'aria-val'},
        text=long_text,
    )
    desc = get_click_description(node)
    # Should include truncated text in quotes
    assert '"' in desc
    assert desc.count('"') == 2  # exactly one quoted short_text
    # Check truncation pattern: 30 chars then '...'
    assert '"' + ('x' * 30) + '...' + '"' in desc
    # Check that id/name/aria-label tokens are present and id was truncated to 20 in the output
    assert 'id=my-very-long-id-which' in desc or 'id=my-very-long-id-wh' in desc
    assert 'name=n' in desc
    assert 'aria-label=aria-val' in desc
