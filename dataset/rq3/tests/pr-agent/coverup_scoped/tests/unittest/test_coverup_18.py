# file: pr_agent/tools/pr_help_docs.py:421-455
# asked: {"lines": [422, 423, 424, 425, 426, 427, 429, 430, 431, 432, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 448, 449, 450, 452, 453, 454, 455], "branches": [[426, 427], [426, 429], [431, 432], [431, 438], [432, 434], [432, 438], [434, 432], [434, 435], [435, 432], [435, 436], [436, 435], [436, 437], [439, 440], [439, 448], [442, 443], [442, 448]]}
# gained: {"lines": [422, 423, 424, 425, 426, 427, 429, 430, 431, 432, 434, 435, 436, 437, 438, 439, 440, 441, 442, 448, 449, 450, 452, 453, 454, 455], "branches": [[426, 427], [426, 429], [431, 432], [432, 434], [432, 438], [434, 432], [434, 435], [435, 432], [435, 436], [436, 437], [439, 440], [442, 448]]}

import os
from types import SimpleNamespace
import tempfile
import pytest

import pr_agent.tools.pr_help_docs as pr_help_docs_module
from pr_agent.tools.pr_help_docs import PRHelpDocs

def make_fake_clone_return(path_to_return):
    class FakeReturned:
        def __init__(self, path):
            self.path = path
    def clone(repo_url, tmp_dir, remove_dest_folder=False):
        # ignore the tmp_dir param and return object pointing to path_to_return
        return FakeReturned(path_to_return)
    return clone

def test_gen_filenames_to_contents_map_success(monkeypatch, tmp_path):
    # Setup a fake repository structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # create README in root
    readme = repo_root / "README.md"
    readme.write_text("# Root Readme")
    # create docs directory and a doc file
    docs_dir = repo_root / "docs"
    docs_dir.mkdir()
    guide = docs_dir / "guide.md"
    guide.write_text("Guide contents")

    # Create a PRHelpDocs instance without calling __init__
    pr = PRHelpDocs.__new__(PRHelpDocs)
    # set required attributes used by the method
    pr.repo_url = "https://example.com/repo"
    pr.include_root_readme_file = True
    pr.docs_path = "docs"
    pr.supported_doc_exts = [".md"]
    pr.ctx_url = "ctx"
    # fake git provider whose clone returns an object with .path set to repo_root
    fake_git_provider = SimpleNamespace()
    fake_git_provider.clone = make_fake_clone_return(str(repo_root))
    pr.git_provider = fake_git_provider

    # monkeypatch instance method _find_all_document_files_matching_exts to return the docs file
    def fake_find_all(abs_docs_path, ignore_readme=False, max_allowed_files=5000):
        # ensure path is what we expect
        assert os.path.abspath(abs_docs_path) == os.path.abspath(str(docs_dir))
        return [os.path.join(abs_docs_path, "guide.md")]
    pr._find_all_document_files_matching_exts = fake_find_all

    # monkeypatch the map_documentation_files_to_contents function to capture calls and return a known dict
    called = {}
    def fake_map(root_path, doc_files):
        called['root'] = root_path
        called['doc_files'] = list(doc_files)
        return {"file_count": len(doc_files)}
    monkeypatch.setattr(pr_help_docs_module, "map_documentation_files_to_contents", fake_map)

    # Call the method under test
    result = pr._gen_filenames_to_contents_map_from_repo()

    # Assertions: should return the dict from our fake_map and map should have been called with expected args
    assert result == {"file_count": 2}
    assert os.path.abspath(called['root']) == os.path.abspath(str(repo_root))
    # Expect README (root) and docs/guide.md
    expected_files = {os.path.abspath(str(readme)), os.path.abspath(str(guide))}
    assert set(os.path.abspath(p) for p in called['doc_files']) == expected_files

def test_gen_filenames_to_contents_map_clone_failure_returns_empty(monkeypatch):
    # Create a PRHelpDocs instance without calling __init__
    pr = PRHelpDocs.__new__(PRHelpDocs)
    pr.repo_url = "https://example.com/repo"
    pr.include_root_readme_file = True
    pr.docs_path = "docs"
    pr.supported_doc_exts = [".md"]
    pr.ctx_url = "ctx"

    # fake git provider whose clone returns None to trigger exception branch
    fake_git_provider = SimpleNamespace()
    def clone_returns_none(repo_url, tmp_dir, remove_dest_folder=False):
        return None
    fake_git_provider.clone = clone_returns_none
    pr.git_provider = fake_git_provider

    # Ensure map_documentation_files_to_contents is not called; but set a sentinel if it is
    called = {"called": False}
    def fake_map(root_path, doc_files):
        called["called"] = True
        return {"should_not": "be_called"}
    monkeypatch.setattr(pr_help_docs_module, "map_documentation_files_to_contents", fake_map)

    # Call the method under test - should catch exception and return {}
    result = pr._gen_filenames_to_contents_map_from_repo()
    assert result == {}
    assert called["called"] is False
