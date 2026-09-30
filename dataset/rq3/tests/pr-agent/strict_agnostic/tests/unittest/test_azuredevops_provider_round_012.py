import types
import pytest
from types import SimpleNamespace

import pr_agent.git_providers.azuredevops_provider as azmod
from pr_agent.git_providers.azuredevops_provider import AzureDevopsProvider
from pr_agent.algo.types import EDIT_TYPE

# All test functions end with _round_012 as required.

def make_provider_instance():
    # Instantiate without __init__ to avoid side effects; populate required attrs.
    prov = AzureDevopsProvider.__new__(AzureDevopsProvider)
    prov.diff_files = None
    prov.repo_slug = "repo"
    prov.pr_num = 1
    prov.workspace_slug = "proj"
    # Simple PR-like object with commit ids
    prov.pr = SimpleNamespace(last_merge_target_commit=SimpleNamespace(commit_id="base123"),
                              last_merge_commit=SimpleNamespace(commit_id="head456"))
    return prov


def test_prepopulated_diff_files_round_012():
    # If diff_files already present, the method should return it immediately (early return branch).
    prov = make_provider_instance()
    sentinel = ["already"]
    prov.diff_files = sentinel

    result = AzureDevopsProvider.get_diff_files(prov)
    assert result is sentinel


def test_get_diff_files_with_various_change_types_round_012(monkeypatch):
    prov = make_provider_instance()

    # Prepare iteration and change entries to exercise add, delete, renamed, and modified cases.
    change_add = SimpleNamespace(additional_properties={"item": {"path": "a.py"}, "changeType": "add"})
    change_delete = SimpleNamespace(additional_properties={"item": {"path": "b.py"}, "changeType": "delete"})
    change_rename = SimpleNamespace(additional_properties={"item": {"path": "c.py"}, "changeType": "edit, rename"})
    change_edit = SimpleNamespace(additional_properties={"item": {"path": "d.py"}, "changeType": "edit"})

    # azure client fake
    def fake_get_pull_request_iterations(repository_id, pull_request_id, project):
        return [SimpleNamespace(id=9)]

    def fake_get_pull_request_iteration_changes(repository_id, pull_request_id, iteration_id, project):
        return SimpleNamespace(change_entries=[change_add, change_delete, change_rename, change_edit])

    # get_item behavior depends on path and version_descriptor.version
    def fake_get_item(repository_id, path, project, version_descriptor, download, include_content):
        # head versions return new content for all except b.py which was deleted (simulate missing new content)
        if version_descriptor.version == prov.pr.last_merge_commit.commit_id:
            if path == "b.py":
                raise Exception("file deleted in head")
            return SimpleNamespace(content=("+new_line_for_" + path + "\n-removed_for_" + path + "\n"))
        # base versions: for d.py (modified) simulate failure to fetch original -> raise
        if path == "d.py":
            raise Exception("original fetch failed")
        return SimpleNamespace(content=("original_for_" + path + "\n"))

    # load_large_diff returns a predictable patch with plus and minus lines
    def fake_load_large_diff(file, new_file_content_str, original_file_content_str, show_warning=False):
        # Provide a patch that has one plus and one minus line for counting
        return "+added_line\n-removed_line\n context\n"

    # filter_ignored returns unchanged list so no filtering branch
    def fake_filter_ignored(diffs, provider_name):
        return diffs

    # All files are valid
    def fake_is_valid_file(path):
        return True

    # Attach fake azure client
    prov.azure_devops_client = SimpleNamespace(
        get_pull_request_iterations=fake_get_pull_request_iterations,
        get_pull_request_iteration_changes=fake_get_pull_request_iteration_changes,
        get_item=fake_get_item,
    )

    # Monkeypatch module-level helpers
    monkeypatch.setattr(azmod, "filter_ignored", fake_filter_ignored)
    monkeypatch.setattr(azmod, "is_valid_file", fake_is_valid_file)
    monkeypatch.setattr(azmod, "load_large_diff", fake_load_large_diff)

    # Make get_logger() return a no-op logger to avoid noisy output
    class DummyLogger:
        def info(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def exception(self, *args, **kwargs):
            pass

    monkeypatch.setattr(azmod, "get_logger", lambda: DummyLogger())

    # Run the method under test
    results = prov.get_diff_files()

    # Results should be a list of FilePatchInfo-like objects with expected filenames and edit types
    filenames = {r.filename: r for r in results}

    # a.py was added -> EDIT_TYPE.ADDED
    assert "a.py" in filenames
    assert filenames["a.py"].edit_type == EDIT_TYPE.ADDED
    # b.py was deleted -> EDIT_TYPE.DELETED
    assert "b.py" in filenames
    assert filenames["b.py"].edit_type == EDIT_TYPE.DELETED
    # c.py had rename -> EDIT_TYPE.RENAMED
    assert "c.py" in filenames
    assert filenames["c.py"].edit_type == EDIT_TYPE.RENAMED
    # d.py was edited -> EDIT_TYPE.MODIFIED and original fetch failed so original content stored as empty string
    assert "d.py" in filenames
    assert filenames["d.py"].edit_type == EDIT_TYPE.MODIFIED

    # All entries should reflect the patch produced by fake_load_large_diff: 1 plus, 1 minus
    for fp in results:
        assert fp.num_plus_lines == 1
        assert fp.num_minus_lines == 1

    # After call, provider should have cached diff_files
    assert prov.diff_files is results


def test_filtering_triggers_logging_exception_round_012(monkeypatch):
    # This test ensures that when filter_ignored changes the diffs and get_logger().info raises,
    # the exception is swallowed by the function and it proceeds deterministically.
    prov = make_provider_instance()

    change_ignored = SimpleNamespace(additional_properties={"item": {"path": "ignored.py"}, "changeType": "edit"})

    prov.azure_devops_client = SimpleNamespace(
        get_pull_request_iterations=lambda repository_id, pull_request_id, project: [SimpleNamespace(id=1)],
        get_pull_request_iteration_changes=lambda repository_id, pull_request_id, iteration_id, project: SimpleNamespace(change_entries=[change_ignored]),
        get_item=lambda *args, **kwargs: SimpleNamespace(content="+x\n")
    )

    # filter_ignored will remove the only file -> triggers logging branch
    monkeypatch.setattr(azmod, "filter_ignored", lambda diffs, provider_name: [])
    monkeypatch.setattr(azmod, "is_valid_file", lambda path: True)
    monkeypatch.setattr(azmod, "load_large_diff", lambda *a, **k: "+x\n")

    # Make get_logger().info raise to exercise the inner except block (should be swallowed)
    class ExplodingLogger:
        def info(self, *args, **kwargs):
            raise Exception("logging failure")

        def error(self, *args, **kwargs):
            pass

        def exception(self, *args, **kwargs):
            pass

    monkeypatch.setattr(azmod, "get_logger", lambda: ExplodingLogger())

    # Should not raise despite logger.info raising; result should be an empty list because diffs got filtered out
    res = prov.get_diff_files()
    assert res == []
