import os
from unittest.mock import patch
import pytest

from pr_agent.tools.pr_help_docs import PRHelpDocs


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.exceptions = []

    def warning(self, msg):
        self.warnings.append(msg)

    def exception(self, msg):
        self.exceptions.append(msg)


def _make_instance_with_exts(exts):
    # Bypass potentially heavy __init__; only supported_doc_exts is required by the method under test
    inst = PRHelpDocs.__new__(PRHelpDocs)
    inst.supported_doc_exts = exts
    return inst


def test_find_docs_detects_extensions_and_respects_ignore_readme_round_093():
    abs_docs_path = "/fake/docs"
    # supported extensions include leading dot and mixed case to test normalization
    inst = _make_instance_with_exts(['.MD', 'Txt'])

    files = ['README.md', 'file.TXT', 'other.py']
    # Patch os.walk to return a single directory entry
    with patch('pr_agent.tools.pr_help_docs.os.walk', return_value=[(abs_docs_path, [], files)]):
        # Patch logger to verify no warnings/exceptions for this happy-path case
        dummy = DummyLogger()
        with patch('pr_agent.tools.pr_help_docs.get_logger', return_value=dummy):
            result = inst._find_all_document_files_matching_exts(abs_docs_path, ignore_readme=True, max_allowed_files=5000)

    # README.md should be ignored because ignore_readme=True and it's in the root
    # Only file.TXT should match (case-insensitive, dot-stripping of extensions)
    assert result == [os.path.join(abs_docs_path, 'file.TXT')]
    assert dummy.warnings == []
    assert dummy.exceptions == []


def test_find_docs_respects_max_allowed_and_logs_warning_round_093():
    abs_docs_path = "/fake/docs"
    inst = _make_instance_with_exts(['md'])

    files = ['a.md', 'b.md']
    # Walk yields a single root with two matching files
    with patch('pr_agent.tools.pr_help_docs.os.walk', return_value=[(abs_docs_path, [], files)]):
        dummy = DummyLogger()
        with patch('pr_agent.tools.pr_help_docs.get_logger', return_value=dummy):
            # Set max_allowed_files to 1 so we trigger the early return + warning
            result = inst._find_all_document_files_matching_exts(abs_docs_path, ignore_readme=False, max_allowed_files=1)

    # Should return immediately after finding 1 file
    assert result == [os.path.join(abs_docs_path, 'a.md')]
    # Warning message must match the exact formatted string in the implementation
    assert dummy.warnings == [f"Found at least 1 files in {abs_docs_path}, skipping the rest."]
    assert dummy.exceptions == []


def test_find_docs_handles_exception_and_logs_exception_round_093():
    abs_docs_path = "/fake/docs"
    inst = _make_instance_with_exts(['md'])

    # Make os.walk raise to exercise the exception branch
    def walker_raises(path):
        raise RuntimeError("boom")

    with patch('pr_agent.tools.pr_help_docs.os.walk', side_effect=RuntimeError("boom")):
        dummy = DummyLogger()
        with patch('pr_agent.tools.pr_help_docs.get_logger', return_value=dummy):
            result = inst._find_all_document_files_matching_exts(abs_docs_path, ignore_readme=False, max_allowed_files=10)

    # On exception, the function should return an empty list and log an exception message
    assert result == []
    assert dummy.exceptions == ["Unexpected exception thrown. Returning empty list."]
    assert dummy.warnings == []
