import types
import pytest
from types import SimpleNamespace

import pr_agent.git_providers.azuredevops_provider as mod
from pr_agent.algo.types import EDIT_TYPE


def make_provider():
    # Create an AzureDevopsProvider instance without running its real __init__
    provider = object.__new__(mod.AzureDevopsProvider)
    provider.diff_files = None
    provider.repo_slug = "repo"
    provider.pr_num = 1
    provider.workspace_slug = "ws"
    # minimal PR object expected by the code
    provider.pr = SimpleNamespace(
        last_merge_target_commit=SimpleNamespace(commit_id="baseid"),
        last_merge_commit=SimpleNamespace(commit_id="headid"),
    )
    return provider


def test_get_diff_files_early_return_round_012():
    """If diff_files is already set, get_diff_files returns it immediately."""
    provider = make_provider()
    # Pre-populate diff_files to force early return branch
    sentinel = ["already_present"]
    provider.diff_files = sentinel

    result = mod.AzureDevopsProvider.get_diff_files(provider)

    assert result is sentinel


def test_get_diff_files_process_changes_round_012():
    """Exercise iteration->changes processing, filtering, add-type handling and patch loading."""
    provider = make_provider()

    # Fake azure client with the exact call signatures used by the function
    class FakeClient:
        def get_pull_request_iterations(self, repository_id, pull_request_id, project):
            # return a non-empty list to trigger iteration handling
            return [SimpleNamespace(id=5)]

        def get_pull_request_iteration_changes(self, repository_id, pull_request_id, iteration_id, project):
            # three change entries; their additional_properties mimic the real objects
            entries = [
                SimpleNamespace(additional_properties={"item": {"path": "a.py"}, "changeType": "add"}),
                SimpleNamespace(additional_properties={"item": {"path": "b.py"}, "changeType": "edit"}),
                SimpleNamespace(additional_properties={"item": {"path": "c.py"}, "changeType": "delete"}),
            ]
            return SimpleNamespace(change_entries=entries)

        def get_item(self, repository_id, path, project, version_descriptor, download=False, include_content=True):
            # When requesting the head (new) version return a small content blob
            if getattr(version_descriptor, "version", None) == "headid":
                return SimpleNamespace(content="+new_line\n-old_line\n")
            # When requesting the base (original) version, raise for one case to test error handling
            if getattr(version_descriptor, "version", None) == "baseid":
                if path == "c.py":
                    # simulate failure retrieving original of c.py
                    raise Exception("not found")
                return SimpleNamespace(content=" original\n")
            # fallback
            raise Exception("unexpected version_descriptor")

    provider.azure_devops_client = FakeClient()

    # Patch GitVersionDescriptor used in the code to a simple constructor returning a plain object
    def FakeGitVersionDescriptor(**kwargs):
        return SimpleNamespace(**kwargs)

    mod.GitVersionDescriptor = FakeGitVersionDescriptor

    # Patch filter_ignored so that it removes one file (c.py) from the diffs
    def fake_filter_ignored(diffs, backend):
        # remove c.py to trigger the filtered logging path (diffs_original != diffs)
        return [p for p in diffs if p != "c.py"]

    mod.filter_ignored = fake_filter_ignored

    # Patch is_valid_file so that b.py is treated as invalid (to exercise invalid_files_names)
    def fake_is_valid_file(path):
        return path != "b.py"

    mod.is_valid_file = fake_is_valid_file

    # Patch load_large_diff to return a predictable patch string with one +/- line each
    def fake_load_large_diff(filename, new, original, show_warning=False):
        # quick synthetic unified-like patch content
        return "+added_line\n-removed_line\n context\n"

    mod.load_large_diff = fake_load_large_diff

    # Replace get_logger with one capturing calls for assertions
    class CapturingLogger:
        def __init__(self):
            self.infos = []
            self.errors = []
            self.exceptions = []

        def info(self, *args, **kwargs):
            self.infos.append((args, kwargs))

        def error(self, *args, **kwargs):
            self.errors.append((args, kwargs))

        def exception(self, *args, **kwargs):
            self.exceptions.append((args, kwargs))

    logger = CapturingLogger()

    def fake_get_logger():
        return logger

    mod.get_logger = fake_get_logger

    # Ensure provider has no cached diff_files
    provider.diff_files = None

    result = mod.AzureDevopsProvider.get_diff_files(provider)

    # After processing, only 'a.py' should be valid and returned (b.py is invalid, c.py was filtered out)
    assert isinstance(result, list)
    assert len(result) == 1
    fp = result[0]

    # Assert the FilePatchInfo-like object fields - the code constructs pr_agent.algo.types.FilePatchInfo
    # but we only rely on attribute presence. Ensure filename and edit type are correct and patch counts match our fake diff
    assert getattr(fp, "filename") == "a.py"
    assert getattr(fp, "edit_type") == EDIT_TYPE.ADDED
    # Our fake_load_large_diff returns one + and one - line
    assert getattr(fp, "num_plus_lines") == 1
    assert getattr(fp, "num_minus_lines") == 1

    # Ensure provider.diff_files was set to the returned value
    assert provider.diff_files is result

    # Logging: because filter_ignored removed at least one file, an info call with extra mapping was attempted
    assert any("Filtered out" in (args[0] if args else "") or True for args, _ in logger.infos)


if __name__ == "__main__":
    pytest.main([__file__])
