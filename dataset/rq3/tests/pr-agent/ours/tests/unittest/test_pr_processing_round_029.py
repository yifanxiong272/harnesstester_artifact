import types
import pytest

import pr_agent.algo.pr_processing as pr_mod
from pr_agent.algo.pr_processing import pr_generate_compressed_diff


class DummyFile:
    def __init__(self, filename, tokens=0, base_file="", head_file="", patch=None, edit_type="mod"):
        self.filename = filename
        self.tokens = tokens
        self.base_file = base_file
        self.head_file = head_file
        self.patch = patch
        self.edit_type = edit_type


class DummyTokenHandler:
    def __init__(self, value_map=None):
        # value_map can be used to simulate different token counts
        self.value_map = value_map or {}

    def count_tokens(self, value):
        # deterministic: return map value if present else length
        return self.value_map.get(value, len(str(value)))


def make_settings(max_ai_calls):
    # model the minimal shape used in pr_generate_compressed_diff
    s = types.SimpleNamespace()
    s.pr_description = types.SimpleNamespace(max_ai_calls=max_ai_calls)
    return lambda: s


def test_no_files_round_029(monkeypatch):
    """
    When top_langs is empty, function should invoke generate_full_patch once and
    return lists built from its return. This covers the path with no sorted files
    (lines around initial loop and first generate_full_patch call).
    """
    # Patch collaborators
    called = {}

    def fake_generate_full_patch(convert_hunks_to_line_numbers, file_dict, max_tokens_model, remaining_files_list, token_handler):
        # assert expected incoming values for determinism
        assert convert_hunks_to_line_numbers is False
        assert file_dict == {}
        called['max_tokens_model'] = max_tokens_model
        called['remaining_files_list'] = remaining_files_list
        # return deterministic values
        return 42, ["patch_one"], [], ["file_in_patch"]

    monkeypatch.setattr(pr_mod, 'generate_full_patch', fake_generate_full_patch)
    monkeypatch.setattr(pr_mod, 'get_max_tokens', lambda model: 10)

    token_handler = DummyTokenHandler()

    patches_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list = pr_generate_compressed_diff(
        top_langs=[],
        token_handler=token_handler,
        model="any-model",
        convert_hunks_to_line_numbers=False,
        large_pr_handling=False,
    )

    # Oracles: returned values should reflect the fake_generate_full_patch
    assert patches_list == [["patch_one"]]
    assert total_tokens_list == [42]
    assert deleted_files_list == []
    assert remaining_files_list == []
    assert file_dict == {}
    assert files_in_patches_list == [["file_in_patch"]]
    # ensure patched get_max_tokens was used (deterministic check)
    assert called['max_tokens_model'] == 10


def test_deleted_file_round_029(monkeypatch):
    """
    When a file has a truthy patch but handle_patch_deletions returns None,
    the filename must be appended to deleted_files_list and no token counting
    or file_dict insertion should occur for that file.
    """
    file = DummyFile(filename="deleted.py", tokens=3, base_file="b", head_file="h", patch="orig-patch")
    top_langs = [{"files": [file]}]

    # handle_patch_deletions returns None -> marks as deleted
    monkeypatch.setattr(pr_mod, 'handle_patch_deletions', lambda patch, base, head, filename, edit_type: None)

    # generate_full_patch should still be called with empty file_dict
    monkeypatch.setattr(pr_mod, 'generate_full_patch', lambda convert_hunks_to_line_numbers, file_dict, max_tokens_model, remaining_files_list, token_handler: (0, [], [], []))
    monkeypatch.setattr(pr_mod, 'get_max_tokens', lambda model: 15)

    token_handler = DummyTokenHandler()

    patches_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list = pr_generate_compressed_diff(
        top_langs=top_langs,
        token_handler=token_handler,
        model="m",
        convert_hunks_to_line_numbers=False,
        large_pr_handling=False,
    )

    # Oracles: file should be registered as deleted and no entries in file_dict
    assert deleted_files_list == ["deleted.py"]
    assert file_dict == {}
    assert patches_list == [[]] or patches_list == [[]]  # first iteration yields empty patches
    assert total_tokens_list == [0]
    assert files_in_patches_list == [[]]


def test_convert_hunks_and_large_pr_handling_round_029(monkeypatch):
    """
    Test the branch where a patch is kept, converted to hunks with line numbers,
    counted for tokens, and then multiple iterations of large PR handling append
    additional patches. This exercises convert_hunks_to_line_numbers True and
    the additional-iterations loop when remaining files are present.
    """
    file = DummyFile(filename="f1.py", tokens=10, base_file="orig", head_file="head", patch="orig_patch", edit_type="mod")
    top_langs = [{"files": [file]}]

    # make handle_patch_deletions return a non-None patch (so file is kept)
    monkeypatch.setattr(pr_mod, 'handle_patch_deletions', lambda patch, base, head, filename, edit_type: "patched_content")

    # decouple_and_convert_to_hunks_with_lines_numbers should be called and return converted patch
    monkeypatch.setattr(pr_mod, 'decouple_and_convert_to_hunks_with_lines_numbers', lambda patch, file_obj: "converted_patch")

    # Token handler should deterministically return 5 for the converted patch
    token_handler = DummyTokenHandler(value_map={"converted_patch": 5})

    # get_max_tokens deterministic
    monkeypatch.setattr(pr_mod, 'get_max_tokens', lambda model: 100)

    # generate_full_patch should be invoked twice: first call returns a remaining_files_list that is non-empty,
    # second call returns remaining_files_list empty and a second patch to append.
    sequence = [
        (5, ["patchA"], ["f1.py"], ["filesA"]),
        (7, ["patchB"], [], ["filesB"]),
    ]

    def fake_generate_full_patch(convert_hunks_to_line_numbers, file_dict, max_tokens_model, remaining_files_list, token_handler_arg):
        # pop the next value from sequence
        return sequence.pop(0)

    monkeypatch.setattr(pr_mod, 'generate_full_patch', fake_generate_full_patch)

    # patch get_settings so NUMBER_OF_ALLOWED_ITERATIONS yields 2 -> loop range(1) executes once
    monkeypatch.setattr(pr_mod, 'get_settings', make_settings(max_ai_calls=3))

    patches_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list = pr_generate_compressed_diff(
        top_langs=top_langs,
        token_handler=token_handler,
        model="m",
        convert_hunks_to_line_numbers=True,
        large_pr_handling=True,
    )

    # Oracles: ensure the converted patch was tokenized and file_dict contains it
    assert file.filename in file_dict
    assert file_dict[file.filename]['patch'] == "converted_patch"
    assert file_dict[file.filename]['tokens'] == 5
    assert file_dict[file.filename]['edit_type'] == file.edit_type

    # The generate_full_patch side effect produced two appended patches
    assert patches_list == [["patchA"], ["patchB"]]
    assert total_tokens_list == [5, 7]
    assert files_in_patches_list == [["filesA"], ["filesB"]]
    # No deleted files in this scenario
    assert deleted_files_list == []
    # Final remaining files list should match the last returned value (empty)
    assert remaining_files_list == []
