# file: browser_use/dom/serializer/serializer.py:1087-1290
# asked: {"lines": [1116, 1117, 1118, 1119, 1120, 1121, 1125, 1131, 1133, 1135, 1137, 1139, 1142, 1151, 1152, 1154, 1156, 1160, 1161, 1162, 1163, 1166, 1167, 1170, 1171, 1172, 1173, 1175, 1176, 1198, 1203, 1204, 1221, 1222, 1223, 1224, 1225, 1228, 1254, 1258, 1262, 1267, 1271, 1276, 1285, 1290], "branches": [[1093, 1110], [1110, 1180], [1115, 1116], [1128, 1180], [1130, 1131], [1132, 1133], [1134, 1135], [1136, 1137], [1138, 1139], [1141, 1142], [1149, 1151], [1152, 1154], [1152, 1180], [1158, 1160], [1161, 1162], [1161, 1166], [1169, 1170], [1171, 1172], [1171, 1175], [1193, 1191], [1197, 1198], [1201, 1191], [1208, 1227], [1212, 1227], [1213, 1227], [1215, 1221], [1217, 1213], [1221, 1213], [1221, 1222], [1223, 1213], [1223, 1224], [1227, 1228], [1233, 1252], [1253, 1254], [1257, 1258], [1261, 1262], [1266, 1267], [1270, 1271], [1275, 1276], [1278, 1290], [1284, 1285]]}
# gained: {"lines": [1116, 1117, 1118, 1119, 1120, 1121, 1125, 1131, 1133, 1135, 1137, 1139, 1142, 1151, 1152, 1154, 1156, 1160, 1161, 1162, 1163, 1166, 1167, 1170, 1171, 1172, 1173, 1175, 1176, 1198, 1203, 1204, 1228, 1254, 1258, 1262, 1267, 1271, 1276, 1290], "branches": [[1093, 1110], [1110, 1180], [1115, 1116], [1128, 1180], [1130, 1131], [1132, 1133], [1134, 1135], [1136, 1137], [1138, 1139], [1141, 1142], [1149, 1151], [1152, 1154], [1158, 1160], [1161, 1162], [1161, 1166], [1169, 1170], [1171, 1172], [1171, 1175], [1193, 1191], [1197, 1198], [1208, 1227], [1212, 1227], [1227, 1228], [1233, 1252], [1253, 1254], [1257, 1258], [1261, 1262], [1266, 1267], [1270, 1271], [1275, 1276], [1278, 1290]]}

import pytest
from types import SimpleNamespace
from browser_use.dom.serializer.serializer import DOMTreeSerializer


class Prop:
    def __init__(self, name, value):
        self.name = name
        self._value = value

    @property
    def value(self):
        return self._value


class PropBad:
    def __init__(self, name):
        self.name = name

    @property
    def value(self):
        raise AttributeError("bad prop")


class AXNode:
    def __init__(self, properties=None, role=None):
        self.properties = properties or []
        self.role = role


def make_node(attributes=None, tag_name=None, node_name=None, ax_node=None):
    # Minimal duck-typed node expected by _build_attributes_string
    return SimpleNamespace(
        attributes=attributes or {},
        tag_name=tag_name,
        node_name=node_name or (tag_name or '').lower(),
        ax_node=ax_node,
    )


def attrs_to_tokens(s):
    """Split attribute string into tokens key=value or key=''."""
    if not s:
        return []
    return s.split(' ')


def assert_has(token, out):
    assert token in out.split(' '), f"Expected token {token!r} in output {out!r}"


def assert_not_has(token, out):
    assert token not in out.split(' '), f"Did not expect token {token!r} in output {out!r}"


def test_date_input_format_and_placeholder():
    node = make_node(attributes={'type': 'date'}, tag_name='input', node_name='input')
    out = DOMTreeSerializer._build_attributes_string(node, ['format', 'placeholder'], text='')
    # Should include both format and placeholder for HTML5 date input
    assert_has('format=YYYY-MM-DD', out)
    assert_has('placeholder=YYYY-MM-DD', out)


@pytest.mark.parametrize(
    "itype,expected_placeholder,expected_format",
    [
        ('time', 'HH:MM', 'HH:MM'),
        ('datetime-local', 'YYYY-MM-DDTHH:MM', 'YYYY-MM-DDTHH:MM'),
        ('month', 'YYYY-MM', 'YYYY-MM'),
        ('week', 'YYYY-W##', 'YYYY-W##'),
    ],
)
def test_various_html5_input_types(itype, expected_placeholder, expected_format):
    node = make_node(attributes={'type': itype}, tag_name='input', node_name='input')
    out = DOMTreeSerializer._build_attributes_string(node, ['format', 'placeholder'], text='')
    assert_has(f'format={expected_format}', out)
    assert_has(f'placeholder={expected_placeholder}', out)


def test_tel_placeholder_when_no_pattern_and_pattern_present():
    # When no 'pattern' attribute in attributes_to_include, tel gets a phone placeholder
    node = make_node(attributes={'type': 'tel'}, tag_name='input', node_name='input')
    out = DOMTreeSerializer._build_attributes_string(node, ['placeholder'], text='')
    assert_has('placeholder=123-456-7890', out)
    # If pattern present in the initial attributes and included, placeholder should not be added
    node2 = make_node(attributes={'type': 'tel', 'pattern': r'\d{3}-\d{3}-\d{4}'}, tag_name='input', node_name='input')
    out2 = DOMTreeSerializer._build_attributes_string(node2, ['pattern', 'placeholder'], text='')
    # pattern should be present; placeholder should not
    assert_has("pattern=\\d{3}-\\d{3}-\\d{4}", out2)
    assert_not_has("placeholder=123-456-7890", out2)


def test_uib_datepicker_popup_expected_format_and_format():
    # Include 'placeholder' to trigger the branch which handles uib-datepicker-popup
    node = make_node(attributes={'type': 'text', 'uib-datepicker-popup': 'MM/dd/yyyy'}, tag_name='input', node_name='input')
    out = DOMTreeSerializer._build_attributes_string(node, ['expected_format', 'format', 'placeholder'], text='')
    assert_has('expected_format=MM/dd/yyyy', out)
    assert_has('format=MM/dd/yyyy', out)


def test_jquery_datepicker_with_and_without_data_date_format():
    # With data-date-format
    node = make_node(attributes={'type': 'text', 'class': 'datepicker', 'data-date-format': 'dd-mm-yyyy'}, tag_name='input', node_name='input')
    out = DOMTreeSerializer._build_attributes_string(node, ['placeholder', 'format'], text='')
    assert_has('placeholder=dd-mm-yyyy', out)
    assert_has('format=dd-mm-yyyy', out)
    # Without data-date-format should default to mm/dd/yyyy
    node2 = make_node(attributes={'type': 'text', 'class': 'datetimepicker'}, tag_name='input', node_name='input')
    out2 = DOMTreeSerializer._build_attributes_string(node2, ['placeholder', 'format'], text='')
    assert_has('placeholder=mm/dd/yyyy', out2)
    assert_has('format=mm/dd/yyyy', out2)


def test_data_datepicker_attr_with_and_without_format():
    node = make_node(attributes={'type': 'text', 'data-datepicker': '1', 'data-date-format': 'YYYY'}, tag_name='input', node_name='input')
    out = DOMTreeSerializer._build_attributes_string(node, ['placeholder', 'format'], text='')
    assert_has('placeholder=YYYY', out)
    assert_has('format=YYYY', out)
    node2 = make_node(attributes={'type': 'text', 'data-datepicker': '1'}, tag_name='input', node_name='input')
    out2 = DOMTreeSerializer._build_attributes_string(node2, ['placeholder', 'format'], text='')
    assert_has('placeholder=mm/dd/yyyy', out2)
    assert_has('format=mm/dd/yyyy', out2)


def test_password_field_hides_values():
    # Both DOM attribute 'value' and AX 'value' should not be included for password fields
    ax = AXNode(properties=[Prop('value', 'secret')])
    node = make_node(attributes={'type': 'password', 'value': 'secret'}, tag_name='input', node_name='input', ax_node=ax)
    out = DOMTreeSerializer._build_attributes_string(node, ['value'], text='')
    # Should not include value at all
    assert out == ''


def test_ax_properties_boolean_and_bad_prop_handling():
    # Boolean property should be lowercased
    ax = AXNode(properties=[Prop('checked', True)])
    node = make_node(attributes={}, tag_name=None, node_name='div', ax_node=ax)
    out = DOMTreeSerializer._build_attributes_string(node, ['checked'], text='')
    assert_has('checked=true', out)
    # Bad prop that raises AttributeError should be ignored and not crash
    ax2 = AXNode(properties=[PropBad('foo')])
    node2 = make_node(attributes={}, tag_name=None, node_name='div', ax_node=ax2)
    out2 = DOMTreeSerializer._build_attributes_string(node2, ['foo'], text='')
    assert out2 == ''


def test_textarea_valuetext_preferred_over_value():
    ax = AXNode(properties=[Prop('valuetext', 'Displayed'), Prop('value', 'Raw')])
    node = make_node(attributes={}, tag_name='textarea', node_name='textarea', ax_node=ax)
    out = DOMTreeSerializer._build_attributes_string(node, ['value'], text='')
    # valuetext should be used to set 'value'
    assert_has('value=Displayed', out)


def test_duplicate_value_removal_and_protected_attrs():
    # Two attributes with same long value >5 should cause one to be removed.
    long_val = 'abcdefghijk'  # length > 5
    attributes = {'a': long_val, 'b': long_val, 'format': long_val}
    node = make_node(attributes=attributes, tag_name='div', node_name='div')
    out = DOMTreeSerializer._build_attributes_string(node, ['a', 'b', 'format'], text='')
    tokens = attrs_to_tokens(out)
    # 'format' is protected and should remain; only one of a/b should remain so count of long_val tokens is 2
    present_vals = [t for t in tokens if long_val in t]
    assert len(present_vals) == 2
    assert any(t.startswith('format=') for t in tokens)


def test_role_and_type_and_invalid_and_required_and_expanded_and_matching_text_removal():
    # role removal when node.node_name == ax_node.role
    ax = AXNode(role='button')
    node = make_node(attributes={'role': 'button'}, tag_name='button', node_name='button', ax_node=ax)
    out = DOMTreeSerializer._build_attributes_string(node, ['role'], text='')
    assert out == ''  # role removed

    # type removal when type matches node_name
    node2 = make_node(attributes={'type': 'button'}, tag_name='button', node_name='button')
    out2 = DOMTreeSerializer._build_attributes_string(node2, ['type'], text='')
    assert out2 == ''  # type removed

    # invalid=false removal
    node3 = make_node(attributes={'invalid': 'false'}, tag_name='div', node_name='div')
    out3 = DOMTreeSerializer._build_attributes_string(node3, ['invalid'], text='')
    assert out3 == ''

    # required false removal
    node4 = make_node(attributes={'required': 'false'}, tag_name='div', node_name='div')
    out4 = DOMTreeSerializer._build_attributes_string(node4, ['required'], text='')
    assert out4 == ''

    # aria-expanded removal when expanded present
    node5 = make_node(attributes={'expanded': 'true', 'aria-expanded': 'no'}, tag_name='div', node_name='div')
    out5 = DOMTreeSerializer._build_attributes_string(node5, ['expanded', 'aria-expanded'], text='')
    # expanded should remain, aria-expanded removed
    assert_has('expanded=true', out5)
    assert_not_has('aria-expanded=no', out5)

    # remove attrs if they match text (case-insensitive)
    node6 = make_node(attributes={'placeholder': 'Hello', 'title': 'World'}, tag_name='div', node_name='div')
    out6 = DOMTreeSerializer._build_attributes_string(node6, ['placeholder', 'title'], text='hello')
    # placeholder should be removed because it matches text; title remains
    assert_not_has('placeholder=Hello', out6)
    assert_has('title=World', out6)


def test_empty_value_results_in_no_attribute_inclusion():
    # Attributes with empty string values are intentionally ignored by the serializer's initial filtering,
    # so the expected output is empty.
    node = make_node(attributes={'data': ''}, tag_name='div', node_name='div')
    out = DOMTreeSerializer._build_attributes_string(node, ['data'], text='')
    assert out == ''


def test_returns_empty_when_no_attributes_to_include():
    node = make_node(attributes={}, tag_name='div', node_name='div', ax_node=None)
    out = DOMTreeSerializer._build_attributes_string(node, [], text='')
    assert out == ''
