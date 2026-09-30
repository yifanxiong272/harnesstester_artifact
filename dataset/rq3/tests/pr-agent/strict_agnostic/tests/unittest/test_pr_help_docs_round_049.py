import os
from types import SimpleNamespace
import pr_agent.tools.pr_help_docs as pr_help_docs
import pytest


def test_clone_failure_round_049():
    """
    Simulate git clone failure (clone returns falsy). Expect the method to catch the
    raised Exception and return an empty dict.
    """
    fake = SimpleNamespace()
    fake.repo_url = "https://example.com/repo.git"
    # clone returns falsy -> triggers raise Exception branch inside the function,
    # which gets caught and yields an empty dict.
    fake.git_provider = SimpleNamespace(clone=lambda repo, tmp_dir, remove_dest_folder=False: None)
    fake.include_root_readme_file = False
    fake.docs_path = "docs"
    fake.supported_doc_exts = [".md", ".rst"]
    fake.ctx_url = "http://ctx"

    result = pr_help_docs.PRHelpDocs._gen_filenames_to_contents_map_from_repo(fake)
    assert result == {}, "Expected empty dict when clone fails"


def test_include_readme_and_map_round_049(monkeypatch):
    """
    Simulate a successful clone where the repository root contains a README file.
    Ensure the README is discovered and that map_documentation_files_to_contents is
    called with the expected base_path and doc_files list. Return a deterministic
    mapping from the stubbed mapper.
    """
    recorded = {}

    def clone(repo_url, tmp_dir, remove_dest_folder=False):
        # create a README in the provided tmp_dir and return an object with .path
        os.makedirs(tmp_dir, exist_ok=True)
        readme_path = os.path.join(tmp_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Example README\nSome docs content\n")
        return SimpleNamespace(path=tmp_dir)

    def fake_mapper(base_path, doc_files):
        # record inputs and return a deterministic mapping
        recorded['base_path'] = base_path
        # normalize paths for easier assertions
        recorded['doc_files'] = [os.path.basename(p) for p in doc_files]
        return {"README.md": "# Example README\nSome docs content\n"}

    fake = SimpleNamespace()
    fake.repo_url = "https://example.com/repo.git"
    fake.git_provider = SimpleNamespace(clone=clone)
    fake.include_root_readme_file = True
    fake.docs_path = "docs"
    fake.supported_doc_exts = [".md"]
    fake.ctx_url = "http://ctx"

    # Patch the module-level mapper to our deterministic stub
    monkeypatch.setattr(pr_help_docs, "map_documentation_files_to_contents", fake_mapper)

    result = pr_help_docs.PRHelpDocs._gen_filenames_to_contents_map_from_repo(fake)

    assert result == {"README.md": "# Example README\nSome docs content\n"}
    # ensure the mapper saw a base_path value and README.md as a discovered file
    assert 'base_path' in recorded and isinstance(recorded['base_path'], str) and recorded['base_path']
    assert 'README.md' in recorded.get('doc_files', [])


def test_no_docs_found_round_049():
    """
    Simulate a repository where a docs directory exists but _find_all_document_files_matching_exts
    returns an empty list. This should trigger the warning branch and cause the
    function to return an empty dict.
    """
    def clone(repo_url, tmp_dir, remove_dest_folder=False):
        # create a docs directory but put no matching doc files inside
        docs_dir = os.path.join(tmp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        return SimpleNamespace(path=tmp_dir)

    # build a fake instance and attach a stubbed _find_all_document_files_matching_exts
    fake = SimpleNamespace()
    fake.repo_url = "https://example.com/repo.git"
    fake.git_provider = SimpleNamespace(clone=clone)
    fake.include_root_readme_file = False
    fake.docs_path = "docs"
    fake.supported_doc_exts = [".md"]
    fake.ctx_url = "http://ctx"

    # The method in the implementation is called as an attribute on the instance.
    # Provide an attribute on the fake instance that accepts the same parameters and
    # returns an empty list to simulate "no docs found" under the docs path.
    def stub_find_all(abs_docs_path, ignore_readme=False, max_allowed_files=None):
        # abs_docs_path should exist at call time (it is created in clone)
        assert os.path.exists(abs_docs_path)
        return []

    fake._find_all_document_files_matching_exts = stub_find_all

    result = pr_help_docs.PRHelpDocs._gen_filenames_to_contents_map_from_repo(fake)
    assert result == {}, "Expected empty dict when docs directory exists but no docs found"
