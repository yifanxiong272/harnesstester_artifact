import types
from aider.commands import Commands


def test_get_help_md_mixed_round_118():
    # Instantiate Commands without calling its heavy __init__
    inst = object.__new__(Commands)

    # Provide an unsorted set of commands that will exercise sorting,
    # the hyphen-to-underscore replacement, an existing method with
    # a docstring, an existing method without a docstring (None),
    # and a command with no corresponding method (else branch).
    inst.get_commands = lambda: [':z', ':do-something', ':ask']

    # Define a method that will match ':do-something' after replacement
    def cmd_do_something():
        "Do something docs"
        pass

    # Define a method that will match ':ask' but has no docstring (None)
    def cmd_ask():
        pass

    # Attach functions as instance attributes. We don't need bound methods;
    # get_help_md only inspects the attribute and its __doc__.
    inst.cmd_do_something = cmd_do_something
    inst.cmd_ask = cmd_ask

    # Call the real implementation under test
    result = Commands.get_help_md(inst)

    # Build expected string precisely as the function assembles it.
    expected = (
        "\n|Command|Description|\n"
        "|:------|:----------|\n"
        "| **:ask** | None |\n"
        "| **:do-something** | Do something docs |\n"
        "| **:z** | |\n"
        "\n"
    )

    assert result == expected
