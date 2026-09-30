# file: sweagent/run/common.py:102-141
# asked: {"lines": [109, 116, 117, 118, 119, 120, 121, 122], "branches": [[108, 109], [114, 116], [119, 120], [119, 121]]}
# gained: {"lines": [109, 116, 117, 118, 119, 120, 121, 122], "branches": [[108, 109], [114, 116], [119, 120], [119, 121]]}

import types
from types import SimpleNamespace

import pytest

from sweagent.run.common import ConfigHelper


def test_get_type_name_full_and_short():
    class MyClass:
        pass

    helper = ConfigHelper()

    full = helper._get_type_name(MyClass, full=True)
    short = helper._get_type_name(MyClass, full=False)

    # full should include module path and end with the class name
    assert full.endswith("MyClass")
    assert "." in full  # contains module path
    # short should be only the class name
    assert short == "MyClass"


def test_value_help_pydantic_and_union_and_get_help():
    helper = ConfigHelper()

    # Create a class that represents a pydantic-like config (has model_fields attr)
    class NestedConfig:
        # model_fields must exist to trigger the pydantic branch in _get_value_help_string
        model_fields = {}

    # 1) pydantic-like item with a description
    desc = "This is a nested config"
    out_with_desc = helper._get_value_help_string(NestedConfig, desc)
    # Should show the short name in green and include the description and the Run --help_option line
    assert "[green]NestedConfig[/green]" in out_with_desc
    assert f"    {desc}" in out_with_desc
    full_name = helper._get_type_name(NestedConfig, full=True)
    assert f"Run [green]--help_option {full_name}[/green] for more info" in out_with_desc

    # 2) pydantic-like item without a description (lines 119-122 branch needs to still run)
    out_no_desc = helper._get_value_help_string(NestedConfig, None)
    assert "[green]NestedConfig[/green]" in out_no_desc
    assert f"    {desc}" not in out_no_desc
    assert f"Run [green]--help_option {full_name}[/green] for more info" in out_no_desc

    # 3) UnionType branch (using `int | str`)
    union_item = int | str
    union_desc = "union description"
    out_union = helper._get_value_help_string(union_item, union_desc)
    # Because the function strips leading/trailing whitespace before returning,
    # the description will not retain leading indentation. Assert presence accordingly.
    assert union_desc in out_union
    assert out_union.strip().startswith(union_desc)
    assert "This config item can be one of the following things" in out_union
    assert "[green]int[/green]" in out_union
    assert "[green]str[/green]" in out_union

    # 4) get_help should iterate model_fields and combine results
    ConfigType = type("ConfigType", (), {})
    ConfigType.model_fields = {
        "nested": SimpleNamespace(annotation=NestedConfig, description="nested-desc"),
        "choices": SimpleNamespace(annotation=union_item, description="choices-desc"),
    }

    help_text = helper.get_help(ConfigType)
    # It should contain both field headers and their help text
    assert "[green][bold]nested[/bold][/green]:" in help_text
    assert "[green][bold]choices[/bold][/green]:" in help_text
    assert "nested-desc" in help_text
    assert "choices-desc" in help_text
    # ensure union options appear in the overall help
    assert "[green]int[/green]" in help_text
    assert "[green]str[/green]" in help_text
