import types
import builtins
import pytest
from types import SimpleNamespace

from pr_agent.algo import pr_processing
from pr_agent.algo.pr_processing import pr_generate_compressed_diff

# Helper to create lightweight file-like objects expected by pr_generate_compressed_diff
class DummyFile:
    def __init__(self, filename, tokens, base_file, head_file, patch, edit_type):
        self.filename = filename
        self.tokens = tokens
        self.base_file = base_file
        self.head_file = head_file
        self.patch = patch
        self.edit_type = edit_type
        # optional attributes that real FilePatchInfo might have
        self.ai_file_summary = None


def test_pr_generate_compressed_diff_basic_round_029(monkeypatch):
    """
    Covers: loop over top_langs, skip files with falsy patch, normal patch handling,
    basic generate_full_patch return used when large_pr_handling is False.
    """
    # Prepare top_langs: one language with a file that has falsy patch, one with a valid patch
    file_no_patch = DummyFile("file_a.txt", tokens=5, base_file="a", head_file="a",
                              patch="", edit_type="modify")
    file_with_patch = DummyFile("file_b.txt", tokens=10, base_file="orig", head_file="new",
                                patch="PATCH_CONTENT", edit_type="modify")

    top_langs = [
        {"files": [file_no_patch]},
        {"files": [file_with_patch]},
    ]

    # token_handler stub
    token_handler = SimpleNamespace()
    token_handler.count_tokens = lambda patch: len(patch) if isinstance(patch, str) else 0

    # Patch external functions used inside pr_generate_compressed_diff
    # handle_patch_deletions should return the same patch (not None)
    monkeypatch.setattr(pr_processing, "handle_patch_deletions", lambda patch, base, head, filename, etype: patch)
    # decouple_and_convert_to_hunks_with_lines_numbers should not be called (convert_hunks_to_line_numbers False in this test)
    monkeypatch.setattr(pr_processing, "decouple_and_convert_to_hunks_with_lines_numbers", lambda patch, file: "SHOULD_NOT_BE_CALLED")

    # get_max_tokens deterministic
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 1000)

    # generate_full_patch: simulate single iteration returning no remaining files
    def fake_generate_full_patch(convert_hunks_to_line_numbers, file_dict, max_tokens_model, remaining_files_list_prev, token_handler_arg):
        # assert we get a file_dict entry for file_b.txt
        assert "file_b.txt" in file_dict
        return 42, ["patch_chunk_1"], [], ["file_b.txt"]

    monkeypatch.setattr(pr_processing, "generate_full_patch", fake_generate_full_patch)

    # Call function under test with convert_hunks_to_line_numbers=False and large_pr_handling=False
    patches_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list = \
        pr_generate_compressed_diff(top_langs, token_handler, model="gpt-test", convert_hunks_to_line_numbers=False, large_pr_handling=False)

    # Assertions (observable deterministic behavior)
    # file with empty patch should be ignored -> not in file_dict and not in deleted_files_list
    assert "file_a.txt" not in file_dict
    # file_b should be present with tokens measured as len(patch)
    assert file_dict["file_b.txt"]["tokens"] == len("PATCH_CONTENT")
    # generate_full_patch returned a single patches list
    assert patches_list == [["patch_chunk_1"]]
    assert total_tokens_list == [42]
    assert deleted_files_list == []
    # no remaining files as fake_generate_full_patch returned []
    assert remaining_files_list == []
    assert files_in_patches_list == [["file_b.txt"]]


def test_pr_generate_compressed_diff_large_pr_round_029(monkeypatch):
    """
    Covers: convert_hunks_to_line_numbers True, decouple conversion, handle_patch_deletions returning None
    (deleted file path), and additional iterations when large_pr_handling True. Also exercises loop
    inside additional iterations (patches present vs no patches leading to break).
    """
    # Prepare a single language with two files to ensure extend() works
    # file1: will get deleted because handle_patch_deletions returns None
    file_deleted = DummyFile("deleted_file.py", tokens=3, base_file="old", head_file="", patch="SOME_PATCH", edit_type="delete")
    # file2: will survive and be converted
    file_keep = DummyFile("keep_file.py", tokens=7, base_file="o", head_file="n", patch="KEEP_PATCH", edit_type="modify")

    top_langs = [{"files": [file_deleted, file_keep]}]

    # token_handler stub: return fixed token counts for visibility
    token_handler = SimpleNamespace()
    def count_tokens(patch):
        if patch == "CONVERTED_KEEP":
            return 200
        return 1
    token_handler.count_tokens = count_tokens

    # handle_patch_deletions: return None for deleted_file to trigger deleted_files_list append, return original for others
    def fake_handle_patch_deletions(patch, base, head, filename, etype):
        if filename == "deleted_file.py":
            return None
        return patch
    monkeypatch.setattr(pr_processing, "handle_patch_deletions", fake_handle_patch_deletions)

    # decouple_and_convert_to_hunks_with_lines_numbers should convert keep patch to marker string
    monkeypatch.setattr(pr_processing, "decouple_and_convert_to_hunks_with_lines_numbers", lambda patch, file: "CONVERTED_KEEP")

    # get_max_tokens deterministic
    monkeypatch.setattr(pr_processing, "get_max_tokens", lambda model: 500)

    # get_settings.pr_description.max_ai_calls: choose 3 so NUMBER_OF_ALLOWED_ITERATIONS = 2 -> loop range(1) -> one extra iteration
    fake_settings = SimpleNamespace()
    fake_settings.pr_description = SimpleNamespace(max_ai_calls=3)
    monkeypatch.setattr(pr_processing, "get_settings", lambda: fake_settings)

    # generate_full_patch: first call returns a remaining file, second call returns no remaining files
    calls = {"count": 0}
    def fake_generate_full_patch(convert_hunks_to_line_numbers, file_dict, max_tokens_model, remaining_files_list_prev, token_handler_arg):
        calls["count"] += 1
        if calls["count"] == 1:
            # first iteration: return one patch and indicate a remaining file
            return 10, ["first_chunk"], ["keep_file.py"], ["keep_file.py"]
        else:
            # second iteration: return another patch and no remaining files -> should cause break after append
            return 5, ["second_chunk"], [], ["keep_file.py"]

    monkeypatch.setattr(pr_processing, "generate_full_patch", fake_generate_full_patch)

    # Call function under test with convert_hunks_to_line_numbers=True and large_pr_handling=True
    patches_list, total_tokens_list, deleted_files_list, remaining_files_list, file_dict, files_in_patches_list = \
        pr_generate_compressed_diff(top_langs, token_handler, model="gpt-large", convert_hunks_to_line_numbers=True, large_pr_handling=True)

    # Assertions to observe branches covered
    # deleted_file should be recorded as deleted
    assert "deleted_file.py" in deleted_files_list
    # keep_file should be present in file_dict with tokens measured from converted patch
    assert file_dict["keep_file.py"]["tokens"] == 200
    # Two iterations produced two appended patch lists
    assert patches_list == [["first_chunk"], ["second_chunk"]]
    # total_tokens_list should reflect both calls
    assert total_tokens_list == [10, 5]
    # remaining_files_list finally should be empty (second call returned [])
    assert remaining_files_list == []
    # files_in_patches_list should contain info from both iterations
    assert files_in_patches_list == [["keep_file.py"], ["keep_file.py"]]
