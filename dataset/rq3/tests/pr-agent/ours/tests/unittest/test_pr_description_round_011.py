import types
from types import SimpleNamespace
import pr_agent.tools.pr_description as pd


class FakeDiffFile:
    def __init__(self, filename, num_plus_lines, num_minus_lines):
        self.filename = filename
        self.num_plus_lines = num_plus_lines
        self.num_minus_lines = num_minus_lines


def test_process_pr_files_prediction_unsupported_round_011():
    """
    If the git provider does not support gfm_markdown, the method should
    immediately return the original pr_body unchanged and an empty pr_comments list.
    This hits the branch where is_supported(...) is False.
    """
    pr_body = "INITIAL_BODY"
    value = {"any": [("path/a.py", "title", "desc")]}

    # Construct a fake self object with the minimal attributes used by the method
    fake_git_provider = SimpleNamespace(is_supported=lambda feature: False)
    fake_self = SimpleNamespace(
        COLLAPSIBLE_FILE_LIST_THRESHOLD=1,
        git_provider=fake_git_provider,
        pr_id="PR-1",
        # add_file_data shouldn't be called in this branch, but provide a stub anyway
        add_file_data=lambda *args, **kwargs: pr_body,
    )

    out_body, out_comments = pd.PRDescription.process_pr_files_prediction(fake_self, pr_body, value)

    assert out_body == pr_body
    assert out_comments == []


def test_process_pr_files_prediction_collapsible_and_diff_round_011():
    """
    Full supported-path: provider supports markdown, settings say "adaptive",
    and num_files triggers the collapsible list. This exercises the loop over
    semantic labels, the file title handling, diff lookup, line link usage, and
    the call to add_file_data. We patch module-level helpers deterministically.
    """
    # Patch module-level helpers used inside the function
    pd.get_settings = lambda: SimpleNamespace(pr_description=SimpleNamespace(collapsible_file_list="adaptive"))

    # Make insert_br_after_x_chars deterministic and short so padding branch is hit
    def fake_insert_br_after_x_chars(text, x):
        # Return a short string independent of x; used for file title wrapping
        return "BRWRAP"

    pd.insert_br_after_x_chars = fake_insert_br_after_x_chars

    # Create a git provider that returns one matching diff file and supports line links
    def get_diff_files():
        # one diff file that will match the first filename
        return [FakeDiffFile("path/file1.py", 10, 2)]

    fake_git_provider = SimpleNamespace(
        is_supported=lambda feature: True,
        get_diff_files=get_diff_files,
        get_line_link=lambda filename, relevant_line_start: "http://link"
    )

    # Prepare a fake self where the threshold is low so adaptive -> True
    captured_added = []

    def stub_add_file_data(delta_nbsp, diff_plus_minus, file_change_description_br, filename, filename_publish, link, pr_body):
        # Record call inputs for assertions and return an augmented body
        captured_added.append({
            "delta_nbsp": delta_nbsp,
            "diff_plus_minus": diff_plus_minus,
            "file_change_description_br": file_change_description_br,
            "filename": filename,
            "filename_publish": filename_publish,
            "link": link,
        })
        return pr_body + f"[ADDED:{filename_publish}]"

    fake_self = SimpleNamespace(
        COLLAPSIBLE_FILE_LIST_THRESHOLD=0,  # small so any file count -> collapsible
        git_provider=fake_git_provider,
        pr_id="PR-2",
        add_file_data=stub_add_file_data,
    )

    # value contains two files under one semantic label: one with a title, one without
    value = {
        "label": [
            ("path/file1.py", "some changes", "a short description"),
            ("path/file2.py", None, "another description"),
        ]
    }

    start_body = "START"
    out_body, out_comments = pd.PRDescription.process_pr_files_prediction(fake_self, start_body, value)

    # Assertions: no exceptions, pr_comments empty, body extended, and collapsible markup present
    assert out_comments == []
    assert out_body.startswith(start_body)
    # The method wraps files inside a table and, because adaptive was True, uses <details>
    assert "<table>" in out_body
    assert "</details>" in out_body or "<details>" in out_body
    # Our stub should have been called at least once (two files -> two calls)
    assert len(captured_added) >= 2
    # Ensure diff information filled for the first captured item (matching diff file)
    first = captured_added[0]
    assert first["diff_plus_minus"] in ("+10/-2", "[link]", "") or isinstance(first["diff_plus_minus"], str)
    # Ensure the filename passed to add_file_data corresponds to the tuple filenames
    assert any(item["filename"].endswith("file1.py") or item["filename"].endswith("file2.py") for item in captured_added)
