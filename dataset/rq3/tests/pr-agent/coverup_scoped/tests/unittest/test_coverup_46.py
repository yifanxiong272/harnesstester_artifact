# file: pr_agent/tools/pr_help_docs.py:396-419
# asked: {"lines": [397, 398, 401, 404, 405, 406, 407, 408, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419], "branches": [[405, 406], [405, 416], [406, 405], [406, 407], [407, 408], [407, 410], [410, 406], [410, 411], [413, 406], [413, 414]]}
# gained: {"lines": [397, 398, 401, 404, 405, 406, 407, 408, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419], "branches": [[405, 406], [405, 416], [406, 405], [406, 407], [407, 408], [407, 410], [410, 411], [413, 406], [413, 414]]}

import pathlib
import pytest

import pr_agent.tools.pr_help_docs as help_docs_mod
from pr_agent.tools.pr_help_docs import PRHelpDocs


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.exceptions = []
        self.debugs = []

    def warning(self, msg):
        self.warnings.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)

    def debug(self, msg):
        self.debugs.append(msg)


def make_instance_without_init():
    # Create instance without invoking __init__
    inst = PRHelpDocs.__new__(PRHelpDocs)
    return inst


def test_find_all_document_files_matching_exts_ignore_readme_and_case_insensitive(tmp_path, monkeypatch):
    # Setup temporary directory structure
    root = tmp_path
    # Files in root
    (root / "README.md").write_text("readme")
    (root / "doc1.MD").write_text("doc1")
    (root / "doc2.md").write_text("doc2")
    # Nested directory
    sub = root / "subdir"
    sub.mkdir()
    (sub / "another.TXT").write_text("txtfile")
    (sub / "notes.TxT").write_text("txt2")

    # Prepare PRHelpDocs instance without running __init__
    ph = make_instance_without_init()
    # include a leading dot and mixed-case to test normalization
    ph.supported_doc_exts = ['.md', 'tXt']

    # Use dummy logger to ensure no real logging side-effects
    dummy = DummyLogger()
    monkeypatch.setattr(help_docs_mod, "get_logger", lambda: dummy)

    # When ignore_readme=True, README.md in root should be skipped
    results = ph._find_all_document_files_matching_exts(str(root), ignore_readme=True, max_allowed_files=5000)
    basenames = {pathlib.Path(p).name for p in results}
    assert "README.md" not in basenames
    # Expect doc1, doc2, another.TXT, notes.TxT (case-insensitive matching)
    assert {"doc1.MD", "doc2.md", "another.TXT", "notes.TxT"} <= basenames
    # No warnings or exceptions should have been recorded
    assert dummy.warnings == []
    assert dummy.exceptions == []

    # When ignore_readme=False, README.md should be included
    results_including_readme = ph._find_all_document_files_matching_exts(str(root), ignore_readme=False, max_allowed_files=5000)
    basenames2 = {pathlib.Path(p).name for p in results_including_readme}
    assert "README.md" in basenames2
    # Ensure at least the same set of other files present
    assert {"doc1.MD", "doc2.md", "another.TXT", "notes.TxT"} <= basenames2


def test_max_allowed_files_triggers_early_return_and_warning(tmp_path, monkeypatch):
    root = tmp_path
    # Create three matching files
    (root / "a.md").write_text("a")
    (root / "b.md").write_text("b")
    (root / "c.md").write_text("c")

    ph = make_instance_without_init()
    ph.supported_doc_exts = ['md']

    dummy = DummyLogger()
    monkeypatch.setattr(help_docs_mod, "get_logger", lambda: dummy)

    # Set max_allowed_files to 2 to force early return
    results = ph._find_all_document_files_matching_exts(str(root), ignore_readme=False, max_allowed_files=2)
    # Should have returned as soon as two files were found
    assert len(results) == 2
    # Ensure a warning was emitted mentioning the limit and directory
    assert any("Found at least 2 files" in msg and str(root) in msg for msg in dummy.warnings)
    assert dummy.exceptions == []


def test_exception_path_returns_empty_list_and_logs_exception(monkeypatch):
    # Make os.walk raise an exception to exercise the except branch
    def raising_walk(*args, **kwargs):
        raise RuntimeError("walk failed")

    ph = make_instance_without_init()
    ph.supported_doc_exts = ['md']

    dummy = DummyLogger()
    monkeypatch.setattr(help_docs_mod, "get_logger", lambda: dummy)
    # Patch the os.walk used inside the module
    monkeypatch.setattr(help_docs_mod.os, "walk", raising_walk)

    results = ph._find_all_document_files_matching_exts("/non/existent/path", ignore_readme=False, max_allowed_files=10)
    # Should return empty list on exception
    assert results == []
    # And the exception should have been logged
    assert any("Unexpected exception thrown. Returning empty list." in msg for msg in dummy.exceptions)
