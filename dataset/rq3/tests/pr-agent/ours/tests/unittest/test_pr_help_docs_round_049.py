import os
from types import SimpleNamespace
import pytest

import pr_agent.tools.pr_help_docs as pr_help_docs_mod
from pr_agent.tools.pr_help_docs import PRHelpDocs


class DummyLogger:
    def __init__(self):
        self.calls = {"debug": 0, "info": 0, "warning": 0, "exception": 0}

    def debug(self, *a, **k):
        self.calls["debug"] += 1

    def info(self, *a, **k):
        self.calls["info"] += 1

    def warning(self, *a, **k):
        self.calls["warning"] += 1

    def exception(self, *a, **k):
        self.calls["exception"] += 1


def make_prhelp_instance():
    # Create instance without running __init__ to avoid external setup.
    inst = object.__new__(PRHelpDocs)
    # Provide minimal attrs used by _gen_filenames_to_contents_map_from_repo
    inst.repo_url = "https://example.com/repo.git"
    inst.include_root_readme_file = False
    inst.docs_path = "docs"
    inst.supported_doc_exts = [".md", ".rst", ".txt"]
    inst.ctx_url = "ctx://example"
    return inst


def test_clone_returns_falsy_results_in_empty_dict_round_049(monkeypatch):
    """
    If git_provider.clone returns a falsy value (None), the method should catch the
    raised exception and return an empty dict. This covers the branch at lines
    around the clone failure path.
    """
    inst = make_prhelp_instance()

    # Dummy logger to capture exception call
    dummy_logger = DummyLogger()
    monkeypatch.setattr(pr_help_docs_mod, "get_logger", lambda: dummy_logger)

    # git_provider.clone returns falsy -> method raises then caught -> return {}
    class FakeGitProvider:
        def clone(self, repo_url, tmp_dir, remove_dest_folder=False):
            return None

    inst.git_provider = FakeGitProvider()

    result = pr_help_docs_mod.PRHelpDocs._gen_filenames_to_contents_map_from_repo(inst)

    assert result == {}, "Expected empty dict when clone fails or returns falsy"
    # ensure exception path was exercised and logger.exception invoked
    assert dummy_logger.calls["exception"] == 1


def test_reads_root_readme_and_calls_map_function_round_049(tmp_path, monkeypatch):
    """
    When include_root_readme_file is True and a README file exists in the
    returned repo root, it should be included in doc_files and passed to
    map_documentation_files_to_contents. This exercises the walk/readme path
    where abs_docs_path does not exist.
    """
    inst = make_prhelp_instance()
    inst.include_root_readme_file = True

    # Create a fake repo dir with a README.md
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    readme = repo_dir / "README.md"
    readme.write_text("# Hello\nThis is README")

    class FakeGitProvider:
        def clone(self, repo_url, tmp_dir_arg, remove_dest_folder=False):
            # Return an object with .path attribute pointing to our repo_dir
            return SimpleNamespace(path=str(repo_dir))

    inst.git_provider = FakeGitProvider()

    # Ensure the docs path does not exist so the code uses only the readme found
    monkeypatch.setattr(pr_help_docs_mod.os.path, "exists", lambda p: False)

    called = {}

    def fake_map_documentation_files_to_contents(base_path, doc_files):
        # record the args and return a deterministic mapping for assertion
        called['base_path'] = base_path
        called['doc_files'] = list(doc_files)
        return {os.path.basename(p): f"contents_of_{os.path.basename(p)}" for p in doc_files}

    monkeypatch.setattr(pr_help_docs_mod, "map_documentation_files_to_contents", fake_map_documentation_files_to_contents)
    monkeypatch.setattr(pr_help_docs_mod, "get_logger", lambda: DummyLogger())

    result = pr_help_docs_mod.PRHelpDocs._gen_filenames_to_contents_map_from_repo(inst)

    # Assert map function was called with the returned repo path
    assert called['base_path'] == str(repo_dir)
    # There should be exactly one README file found
    assert any(p.lower().endswith("readme.md") for p in called['doc_files'])
    # Result should be the mapping produced by fake_map...
    assert "README.md" in result
    assert result["README.md"] == "contents_of_README.md"


def test_abs_docs_exists_but_no_matching_files_returns_empty_round_049(tmp_path, monkeypatch):
    """
    When abs_docs_path exists but _find_all_document_files_matching_exts returns an empty list,
    the function should log a warning and return an empty dict. This covers the branch
    where docs exist but no files matched.
    """
    inst = make_prhelp_instance()
    inst.include_root_readme_file = False
    # prepare fake repo with a docs directory that exists but contains no matching files
    repo_dir = tmp_path / "repo2"
    repo_dir.mkdir()
    docs_dir = repo_dir / "docs"
    docs_dir.mkdir()

    class FakeGitProvider:
        def clone(self, repo_url, tmp_dir_arg, remove_dest_folder=False):
            return SimpleNamespace(path=str(repo_dir))

    inst.git_provider = FakeGitProvider()

    # Force os.path.exists to True only for the docs path
    real_exists = os.path.exists

    def fake_exists(p):
        if p == os.path.join(str(repo_dir), inst.docs_path):
            return True
        return real_exists(p)

    monkeypatch.setattr(pr_help_docs_mod.os.path, "exists", fake_exists)

    # Make _find_all_document_files_matching_exts return empty -> triggers warning and return {}
    monkeypatch.setattr(pr_help_docs_mod, "_find_all_document_files_matching_exts", lambda abs_path, ignore_readme=False, max_allowed_files=None: [])

    dummy_logger = DummyLogger()
    monkeypatch.setattr(pr_help_docs_mod, "get_logger", lambda: dummy_logger)

    result = pr_help_docs_mod.PRHelpDocs._gen_filenames_to_contents_map_from_repo(inst)

    assert result == {}
    # verify that a warning was logged
    assert dummy_logger.calls["warning"] == 1
