# file: aider/coders/base_coder.py:898-910
# asked: {"lines": [899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909], "branches": []}
# gained: {"lines": [899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909], "branches": []}

import types
import pytest

from aider.coders.base_coder import Coder


def make_coder_instance(
    inchat_files,
    abs_read_only_fnames,
    rel_map,
    addable_files,
    commands,
    root,
    edit_format,
    main_model_edit_format,
    io_return,
):
    """
    Create a Coder instance without calling its __init__, and attach the minimal
    attributes/methods needed to exercise get_input().
    """
    coder = object.__new__(Coder)

    # Methods/attributes expected by get_input
    coder.get_inchat_relative_files = lambda: list(inchat_files)
    # get_rel_fname should accept one argument and return mapped relative name
    coder.get_rel_fname = lambda fname: rel_map.get(fname, fname)
    coder.abs_read_only_fnames = list(abs_read_only_fnames)
    coder.get_addable_relative_files = lambda: list(addable_files)
    coder.commands = list(commands)
    coder.root = root
    coder.edit_format = edit_format
    coder.main_model = types.SimpleNamespace(edit_format=main_model_edit_format)

    # IO object with get_input that records call and returns io_return
    recorded = {}
    class DummyIO:
        def get_input(self, root, all_files, addable, commands, abs_read_only_fnames, *, edit_format):
            recorded['root'] = root
            recorded['all_files'] = list(all_files)
            recorded['addable'] = list(addable)
            recorded['commands'] = list(commands)
            recorded['abs_read_only_fnames'] = list(abs_read_only_fnames)
            recorded['edit_format'] = edit_format
            return io_return

    coder.io = DummyIO()
    # expose the recorded dict so tests can assert on it
    coder._io_recorded = recorded
    return coder


def test_get_input_when_edit_format_matches_main_model():
    inchat = ['src/a.py', 'src/b.py']
    abs_ro = ['/abs/ro1.txt', '/abs/ro2.txt']
    rel_map = {
        '/abs/ro1.txt': 'ro1.txt',
        '/abs/ro2.txt': 'ro2.txt',
    }
    addable = ['new/file1.py']
    commands = ['do-nothing']
    root = '/project'
    edit_format = 'same-format'
    main_model_edit_format = 'same-format'  # equal -> expect edit_format passed as ''
    io_return = {'status': 'ok'}

    coder = make_coder_instance(
        inchat_files=inchat,
        abs_read_only_fnames=abs_ro,
        rel_map=rel_map,
        addable_files=addable,
        commands=commands,
        root=root,
        edit_format=edit_format,
        main_model_edit_format=main_model_edit_format,
        io_return=io_return,
    )

    result = Coder.get_input(coder)

    # Verify return value forwarded from IO.get_input
    assert result is io_return

    # Verify IO received expected root
    rec = coder._io_recorded
    assert rec['root'] == root

    # all_files should be sorted unique set of inchat + rel(read-only)
    expected_all = sorted(set(inchat + list(rel_map.values())))
    assert rec['all_files'] == expected_all

    # addable, commands, abs_read_only_fnames passed through
    assert rec['addable'] == addable
    assert rec['commands'] == commands
    assert rec['abs_read_only_fnames'] == abs_ro

    # Because edit_format equals main_model.edit_format, the passed edit_format must be ''
    assert rec['edit_format'] == ''


def test_get_input_when_edit_format_differs_from_main_model():
    inchat = ['z.py', 'a.py']
    abs_ro = ['/abs/x.txt']
    rel_map = {'/abs/x.txt': 'x.txt'}
    addable = []
    commands = []
    root = '/root2'
    edit_format = 'special-format'
    main_model_edit_format = 'default-format'  # different -> expect edit_format passed as 'special-format'
    io_return = ('done', 123)

    coder = make_coder_instance(
        inchat_files=inchat,
        abs_read_only_fnames=abs_ro,
        rel_map=rel_map,
        addable_files=addable,
        commands=commands,
        root=root,
        edit_format=edit_format,
        main_model_edit_format=main_model_edit_format,
        io_return=io_return,
    )

    result = Coder.get_input(coder)

    # Return forwarded
    assert result == io_return

    rec = coder._io_recorded
    # all_files sorted unique set including the read-only mapped filename
    expected_all = sorted(set(inchat + list(rel_map.values())))
    assert rec['all_files'] == expected_all

    # edit_format should be passed through unchanged because it differs from main_model.edit_format
    assert rec['edit_format'] == edit_format

    # other fields forwarded
    assert rec['root'] == root
    assert rec['addable'] == addable
    assert rec['commands'] == commands
    assert rec['abs_read_only_fnames'] == abs_ro
