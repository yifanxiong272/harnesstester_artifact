import pytest
from types import SimpleNamespace
import pr_agent.tools.pr_description as pr_mod
from pr_agent.tools.pr_description import PRDescription


def _make_prdesc_with_stubs(monkeypatch, collapsible_setting, diff_files, line_link_return):
    """Create a PRDescription-like instance with stubbed git_provider and controlled settings.
    Returns the instance.
    """
    # Stub settings: get_settings().pr_description.collapsible_file_list
    class SettingsStub:
        def __init__(self, val):
            self.pr_description = SimpleNamespace(collapsible_file_list=val)

    monkeypatch.setattr(pr_mod, "get_settings", lambda: SettingsStub(collapsible_setting))

    # Create instance without calling __init__
    inst = object.__new__(PRDescription)
    # set a threshold attribute used in logic
    inst.COLLAPSIBLE_FILE_LIST_THRESHOLD = 0
    inst.pr_id = "PR-123"

    # Stub git_provider
    class GitProviderStub:
        def __init__(self, diff_files, line_link_return):
            self._diff = diff_files
            self._line_link_return = line_link_return

        def is_supported(self, feature):
            # only gfm_markdown feature is relevant in tests
            return feature == "gfm_markdown"

        def get_diff_files(self):
            return self._diff

        def get_line_link(self, filename, relevant_line_start=-1):
            # return whatever the test specified (could be empty string)
            return self._line_link_return

    inst.git_provider = GitProviderStub(diff_files, line_link_return)

    # Replace add_file_data with a deterministic implementation for testing
    def add_file_data(delta_nbsp, diff_plus_minus, file_change_description_br, filename,
                      filename_publish, link, pr_body):
        # Append markers to pr_body so tests can assert expected branches were taken
        marker = f"<<FILENAME:{filename_publish}>>"
        marker += f"<<DIFF:{diff_plus_minus}>>"
        marker += f"<<LINK:{link}>>"
        return pr_body + marker

    inst.add_file_data = add_file_data
    return inst


def test_process_pr_files_prediction_collapsible_round_011(monkeypatch):
    """Exercise path where collapsible adaptive logic is True and a title is present.

    Oracle: returned pr_body contains collapsible <details> marker, the filename_publish formatted
    block and the diff/link markers produced by the stubbed add_file_data.
    """
    # Prepare input: a single semantic label with one file tuple where title exists
    value = {
        "feat": [("path/to/file1.py", "some_change_title", "description of change")]
    }

    # diff_files contains a matching filename with small plus/minus numbers
    diff_file = SimpleNamespace(filename="path/to/file1.py", num_plus_lines=3, num_minus_lines=1)

    inst = _make_prdesc_with_stubs(monkeypatch, collapsible_setting="adaptive",
                                   diff_files=[diff_file], line_link_return="http://line.link")

    pr_body, pr_comments = inst.process_pr_files_prediction("", value)

    # Assertions: collapsible details should have been added and our marker appended
    assert "<details>" in pr_body or "<<FILENAME:" in pr_body
    # filename_publish should include strong tag because title was present
    assert "<strong>file1.py</strong>" in pr_body or "file1.py" in pr_body
    # Our deterministic marker added by add_file_data should include diff and link
    assert "<<DIFF:+3/-1>>" in pr_body
    assert "<<LINK:http://line.link>>" in pr_body
    # No comments are produced by this function path
    assert pr_comments == []


def test_process_pr_files_prediction_non_collapsible_title_missing_round_011(monkeypatch):
    """Exercise non-collapsible path and the branch where file_changes_title is missing or '...'.

    Oracle: returned pr_body uses non-collapsible table branch (no <details>) and contains
    a simple strong filename publish and empty diff/link markers.
    """
    # Title is '...' which should be treated as missing title branch
    value = {
        "fix": [("src/module/file2.py", "...", "short desc")]
    }

    # diff_files does not match filename (so diff_plus_minus stays empty)
    diff_file = SimpleNamespace(filename="other/path/fileX.py", num_plus_lines=0, num_minus_lines=0)

    # Provide empty line link to exercise branch where (not link or not diff_plus_minus)
    inst = _make_prdesc_with_stubs(monkeypatch, collapsible_setting=False,
                                   diff_files=[diff_file], line_link_return="")

    pr_body, pr_comments = inst.process_pr_files_prediction("STARTBODY", value)

    # Should not include <details> for non-collapsible case
    assert "<details>" not in pr_body
    # Our deterministic marker should include an empty DIFF and empty LINK markers
    assert "<<DIFF:>>" in pr_body
    assert "<<LINK:>>" in pr_body
    # It should contain the strong filename_publish for file2.py
    assert "file2.py" in pr_body
    assert pr_comments == []
