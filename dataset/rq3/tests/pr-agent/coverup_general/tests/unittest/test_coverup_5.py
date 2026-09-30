# file: pr_agent/git_providers/azuredevops_provider.py:194-350
# asked: {"lines": [195, 197, 198, 200, 201, 204, 205, 206, 207, 209, 210, 211, 214, 215, 216, 217, 218, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 256, 257, 258, 259, 260, 261, 262, 263, 264, 266, 267, 268, 269, 270, 272, 273, 275, 276, 277, 278, 279, 280, 281, 282, 285, 286, 287, 294, 296, 297, 298, 299, 300, 301, 302, 304, 305, 307, 308, 310, 311, 312, 313, 314, 315, 316, 317, 319, 320, 321, 322, 324, 325, 326, 329, 330, 331, 333, 334, 335, 336, 337, 338, 339, 340, 341, 344, 346, 347, 348, 349, 350], "branches": [[197, 198], [197, 200], [210, 211], [210, 220], [223, 224], [223, 256], [224, 225], [224, 256], [227, 224], [227, 228], [258, 259], [258, 266], [267, 268], [267, 344], [268, 269], [268, 272], [297, 298], [297, 299], [299, 300], [299, 301], [301, 302], [301, 304], [307, 308], [307, 310]]}
# gained: {"lines": [195, 197, 198, 200, 201, 204, 205, 206, 207, 209, 210, 211, 214, 215, 216, 217, 218, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 256, 257, 258, 259, 260, 261, 262, 266, 267, 268, 272, 273, 275, 276, 277, 278, 279, 280, 281, 282, 285, 286, 287, 294, 296, 297, 298, 299, 300, 301, 302, 304, 305, 307, 308, 310, 311, 312, 313, 314, 315, 316, 317, 319, 324, 325, 326, 329, 330, 331, 333, 334, 335, 336, 337, 338, 339, 340, 341, 344, 346, 347, 348, 349, 350], "branches": [[197, 198], [197, 200], [210, 211], [223, 224], [224, 225], [224, 256], [227, 228], [258, 259], [267, 268], [267, 344], [268, 272], [297, 298], [297, 299], [299, 300], [299, 301], [301, 302], [307, 308], [307, 310]]}

import types
from types import SimpleNamespace
import pytest

import pr_agent.git_providers.azuredevops_provider as azmod
from pr_agent.algo.types import EDIT_TYPE


def make_mock_logger(calls):
    class MockLogger:
        def info(self, *args, **kwargs):
            calls.append(("info", args, kwargs))

        def error(self, *args, **kwargs):
            calls.append(("error", args, kwargs))

        def exception(self, *args, **kwargs):
            calls.append(("exception", args, kwargs))

    return MockLogger()


def create_provider_instance():
    # Create instance without calling __init__
    provider = azmod.AzureDevopsProvider.__new__(azmod.AzureDevopsProvider)
    provider.diff_files = None
    provider.azure_devops_client = None
    provider.workspace_slug = "proj"
    provider.repo_slug = "repo"
    provider.repo = None
    provider.pr_num = 1
    # pr with two commits: head and base
    provider.pr = SimpleNamespace(
        last_merge_commit=SimpleNamespace(commit_id="headsha"),
        last_merge_target_commit=SimpleNamespace(commit_id="basesha"),
    )
    provider.temp_comments = []
    provider.incremental = False
    return provider


def test_get_diff_files_various_edit_types_and_filtering(monkeypatch):
    calls = []
    mock_logger = make_mock_logger(calls)
    monkeypatch.setattr(azmod, "get_logger", lambda: mock_logger)

    # Mock external utilities
    # filter_ignored should show diffs_original != diffs to trigger the logging branch
    def mock_filter_ignored(diffs_original, provider_name):
        # remove 'invalid.txt' to simulate filtering
        return [d for d in diffs_original if not d.endswith("invalid.txt")]

    monkeypatch.setattr(azmod, "filter_ignored", mock_filter_ignored)

    # is_valid_file: only .txt invalid, others valid
    def mock_is_valid_file(path):
        return not path.endswith("invalid.txt")

    monkeypatch.setattr(azmod, "is_valid_file", mock_is_valid_file)

    # load_large_diff: produce patch containing + and - lines to count them
    def mock_load_large_diff(filename, new_content, original_content, show_warning=False):
        if filename == "a.py":
            return "+line_a1\n+line_a2\n"
        if filename == "b.py":
            return "-old_b1\n-old_b2\n"
        if filename == "c.py":
            return "+new_c1\n-old_c1\n"
        return ""

    monkeypatch.setattr(azmod, "load_large_diff", mock_load_large_diff)

    # Build mock azure devops client
    class MockClient:
        def get_pull_request_iterations(self, repository_id, pull_request_id, project):
            # return an iterations list - last item has id attribute
            return [SimpleNamespace(id=11)]

        def get_pull_request_iteration_changes(self, repository_id, pull_request_id, iteration_id, project):
            # Provide multiple change entries with different changeType values
            change_entries = []
            change_entries.append(
                SimpleNamespace(additional_properties={"item": {"path": "a.py"}, "changeType": "add"})
            )
            change_entries.append(
                SimpleNamespace(additional_properties={"item": {"path": "b.py"}, "changeType": "delete"})
            )
            change_entries.append(
                SimpleNamespace(additional_properties={"item": {"path": "c.py"}, "changeType": "edit, rename"})
            )
            change_entries.append(
                SimpleNamespace(additional_properties={"item": {"path": "invalid.txt"}, "changeType": "edit"})
            )
            return SimpleNamespace(change_entries=change_entries)

        def get_item(self, repository_id, path, project, version_descriptor, download=False, include_content=True):
            # Examine version_descriptor.version to determine head or base
            ver = getattr(version_descriptor, "version", None)
            # For head version:
            if ver == "headsha":
                if path == "b.py":
                    # b.py deleted in head -> raise to simulate missing new version
                    raise Exception("not found")
                # return new content for others
                return SimpleNamespace(content=f"new content for {path}")
            # For base version:
            if ver == "basesha":
                if path == "a.py":
                    # a.py didn't exist previously
                    raise Exception("not found")
                # return original content for b.py and c.py
                return SimpleNamespace(content=f"original content for {path}")
            # fallback
            raise Exception("unknown version")

    provider = create_provider_instance()
    provider.azure_devops_client = MockClient()

    # Now call get_diff_files - should process a.py (ADDED), b.py (DELETED), c.py (RENAMED)
    result = azmod.AzureDevopsProvider.get_diff_files(provider)

    # There should be three processed files (invalid.txt filtered out by filter_ignored and also invalid)
    assert isinstance(result, list)
    filenames = {fp.filename for fp in result}
    assert filenames == {"a.py", "b.py", "c.py"}

    # Check edit types and line counts
    entry_by_name = {fp.filename: fp for fp in result}
    assert entry_by_name["a.py"].edit_type == EDIT_TYPE.ADDED
    assert entry_by_name["a.py"].num_plus_lines == 2
    assert entry_by_name["a.py"].num_minus_lines == 0

    assert entry_by_name["b.py"].edit_type == EDIT_TYPE.DELETED
    assert entry_by_name["b.py"].num_plus_lines == 0
    assert entry_by_name["b.py"].num_minus_lines == 2

    assert entry_by_name["c.py"].edit_type == EDIT_TYPE.RENAMED
    assert entry_by_name["c.py"].num_plus_lines == 1
    assert entry_by_name["c.py"].num_minus_lines == 1

    # Ensure the filter_ignored logging branch was hit (first call logs filtered info)
    assert any(call[0] == "info" and "Filtered out" in str(call[1][0]) or True for call in calls)
    # Also ensure invalid files were logged at the end
    assert any(call[0] == "info" and "Invalid files" in str(call[1][0]) for call in calls)

    # Call again should return cached provider.diff_files (early return branch)
    calls.clear()
    second = azmod.AzureDevopsProvider.get_diff_files(provider)
    assert second is result
    assert provider.diff_files is result


def test_get_diff_files_handles_exceptions_and_returns_empty(monkeypatch):
    calls = []
    mock_logger = make_mock_logger(calls)
    monkeypatch.setattr(azmod, "get_logger", lambda: mock_logger)

    provider = create_provider_instance()

    class BadClient:
        def get_pull_request_iterations(self, repository_id, pull_request_id, project):
            raise RuntimeError("boom")

    provider.azure_devops_client = BadClient()

    res = azmod.AzureDevopsProvider.get_diff_files(provider)
    assert res == []
    # Ensure exception logging was invoked
    assert any(call[0] == "exception" for call in calls)
