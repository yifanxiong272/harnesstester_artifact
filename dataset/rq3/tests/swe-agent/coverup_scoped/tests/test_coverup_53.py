# file: sweagent/tools/utils.py:75-108
# asked: {"lines": [100], "branches": [[95, 97], [97, 100]]}
# gained: {"lines": [100], "branches": [[95, 97], [97, 100]]}

import types
import pytest

from sweagent.tools.utils import generate_command_docs, get_signature


def test_generate_command_docs_with_docstring_and_explicit_signature():
    # Create a simple argument-like object
    class Arg:
        def __init__(self, name, required, type_, description):
            self.name = name
            self.required = required
            self.type = type_
            self.description = description

    # Create a fake command object using SimpleNamespace so it has __dict__
    cmd = types.SimpleNamespace(
        name="do_something",
        # include a format placeholder to ensure kwargs are used
        docstring="Performs action with {tool}",
        signature="do_something <x> [<y>]",
        end_name=None,
        arguments=[Arg("x", True, "str", "first param"), Arg("y", False, "int", "second param")],
    )

    docs = generate_command_docs(commands=[cmd], subroutine_types=[], tool="hammer")

    # Assert docstring formatted and present
    assert "do_something:" in docs
    assert "docstring: Performs action with hammer" in docs

    # Assert explicit signature used (branch where cmd.signature is not None)
    assert "signature: do_something <x> [<y>]" in docs

    # Assert arguments listed with correct required/optional markers and descriptions
    assert "    - x (str) [required]: first param" in docs
    assert "    - y (int) [optional]: second param" in docs


def test_generate_command_docs_uses_get_signature_for_multiline_and_endname():
    # Argument-like object for normal positional args
    class Arg:
        def __init__(self, name, required, type_, description):
            self.name = name
            self.required = required
            self.type = type_
            self.description = description

    # Multi-line last argument: must behave both like an object with attributes
    # and provide a keys() method for get_signature to retrieve the terminating key.
    class LastArg(Arg):
        def keys(self):
            # get_signature expects list(cmd.arguments[-1].keys())[0]
            return [self.name]

    # Create a fake command with end_name set and signature == None to force get_signature usage
    cmd = types.SimpleNamespace(
        name="write_multiline",
        docstring=None,
        signature=None,
        end_name="END",
        # include two normal args, and the last multi-line arg which supplies the terminator key
        arguments=[Arg("a", True, "str", "alpha"), LastArg("EOF", False, "heredoc", "multiline content")],
    )

    docs = generate_command_docs(commands=[], subroutine_types=[cmd])

    # Ensure name printed
    assert "write_multiline:" in docs

    # Docstring is None so no docstring line present
    assert "docstring:" not in docs

    # Since signature is None, get_signature should be called and its output included
    generated_sig = get_signature(cmd)
    assert "signature:" in docs
    # The exact signature may contain newlines; ensure the produced signature from get_signature appears in docs
    assert "EOF" in generated_sig
    assert "END" in generated_sig
    # Confirm that get_signature output is included in the docs text
    assert generated_sig in docs

    # Arguments section should list both arguments (including the last one)
    assert "arguments:" in docs
    assert "    - a (str) [required]: alpha" in docs
    assert "    - EOF (heredoc) [optional]: multiline content" in docs
