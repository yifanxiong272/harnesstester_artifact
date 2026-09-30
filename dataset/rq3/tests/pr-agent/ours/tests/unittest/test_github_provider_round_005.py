import types
import pytest

import pr_agent.git_providers.github_provider as gp


def test_context_diff_files_round_005(monkeypatch):
    """If the starlette_context contains a cached "diff_files" value, get_diff_files should return it immediately."""
    # Ensure GithubProvider does not attempt to create a real GitHub client during init
    monkeypatch.setattr(gp.GithubProvider, "_get_github_client", lambda self: None)

    # Make context.get return a pre-cached diff_files list
    monkeypatch.setattr(gp.context, "get", lambda key, default=None: ["cached_diff"], raising=False)

    provider = gp.GithubProvider()

    result = provider.get_diff_files()

    assert result == ["cached_diff"], "Expected cached diff_files from context to be returned"


def test_get_diff_files_incremental_and_load_large_diff_round_005(monkeypatch):
    """Exercises branches where files are validated, incremental flow is used, load_large_diff is called,
    and invalid files are filtered out. Verifies that resulting FilePatchInfo objects are created and
    that the unreviewed_files_set gets populated with the computed patch."""
    # Prevent real GitHub client creation
    monkeypatch.setattr(gp.GithubProvider, "_get_github_client", lambda self: None)

    # Replace module-level context with a plain dict so final context["diff_files"] assignment works deterministically
    monkeypatch.setattr(gp, "context", {}, raising=False)

    # Ensure MAX_FILES_ALLOWED_FULL is large so avoid_load branch is not triggered here
    monkeypatch.setattr(gp, "MAX_FILES_ALLOWED_FULL", 10, raising=False)

    # Provide deterministic implementations for functions used inside get_diff_files
    monkeypatch.setattr(gp, "load_large_diff", lambda filename, new, orig: "PATCHED", raising=False)

    # is_valid_file: only .py files are valid in this test
    monkeypatch.setattr(gp, "is_valid_file", lambda filename: filename.endswith('.py'), raising=False)

    # Create a fake repo.compare that returns an object with merge_base_commit.sha different than pr.base.sha
    class FakeCompare:
        def __init__(self, sha):
            self.merge_base_commit = types.SimpleNamespace(sha=sha)

    class FakeRepo:
        def __init__(self, mergebase):
            self._mergebase = mergebase

        def compare(self, base_sha, head_sha):
            # return a fake compare object to simulate GitHub compare result
            return FakeCompare(self._mergebase)

    # Fake PR with base and head shas
    fake_pr = types.SimpleNamespace(
        base=types.SimpleNamespace(sha="basesha"),
        head=types.SimpleNamespace(sha="headsha")
    )

    # Create provider and inject fake repo/pr
    provider = gp.GithubProvider()
    provider.repo_obj = FakeRepo(mergebase="mergebase_sha_different")
    provider.pr = fake_pr

    # Provide a fake _get_pr_file_content to return content based on sha argument
    def fake_get_pr_file_content(self, file, sha):
        return f"content-for-{sha}-{file.filename}"

    monkeypatch.setattr(gp.GithubProvider, "_get_pr_file_content", fake_get_pr_file_content, raising=False)

    # Make provider.incremental signal that we're in incremental mode and populate unreviewed_files_set
    provider.incremental = types.SimpleNamespace(is_incremental=True, last_seen_commit_sha="last_seen_sha")
    provider.unreviewed_files_set = {"good.py": "existing"}  # truthy to trigger the incremental branch

    # Fake files returned by get_files: one valid .py, one invalid (filtered out)
    class FakeFile:
        def __init__(self, filename, status, patch=None):
            self.filename = filename
            self.status = status
            self.patch = patch

    files = [FakeFile("good.py", "modified", patch=None), FakeFile("bad.txt", "modified", patch=None)]

    monkeypatch.setattr(provider, "get_files", lambda: files, raising=False)

    # Execute
    diff_files = provider.get_diff_files()

    # Assertions: only the valid .py file should have produced a FilePatchInfo entry
    assert isinstance(diff_files, list)
    assert len(diff_files) == 1

    fp = diff_files[0]
    # FilePatchInfo is constructed with filename argument; expect filename attr to equal 'good.py'
    assert getattr(fp, "filename") == "good.py"

    # The edit type for a 'modified' status should be EDIT_TYPE.MODIFIED
    assert getattr(fp, "edit_type") == gp.EDIT_TYPE.MODIFIED

    # The unreviewed_files_set for the file should have been updated to the value returned by load_large_diff
    assert provider.unreviewed_files_set.get("good.py") == "PATCHED"

    # Also verify that the module context got populated with the diff_files list (assignment at the end of function)
    assert gp.context.get("diff_files") is diff_files
