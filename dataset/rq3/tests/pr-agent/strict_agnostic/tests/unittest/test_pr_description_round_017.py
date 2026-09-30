import pytest
from collections import OrderedDict

from pr_agent.tools.pr_description import PRDescription, PRDescriptionHeader


class DummyGitProvider:
    def __init__(self, supported=None):
        self._supported = set(supported or [])

    def is_supported(self, feature: str) -> bool:
        return feature in self._supported


class DummySettings:
    def __init__(self, **kwargs):
        # attributes expected by the code: enable_pr_type, generate_ai_title, enable_semantic_files_types
        # allow dict-like get for 'file_table_collapsible_open_by_default'
        for k, v in kwargs.items():
            setattr(self, k, v)
        # the code does get_settings().pr_description... so pr_description references itself
        self.pr_description = self

    def get(self, key, default=None):
        return getattr(self, key, default)


@pytest.fixture(autouse=True)
def clean_get_settings(monkeypatch):
    """Ensure we can monkeypatch get_settings used in the module during tests."""
    # Import path used inside pr_agent.tools.pr_description
    import pr_agent.tools.pr_description as mod
    # Provide a placeholder; tests override further as needed
    monkeypatch.setattr(mod, "get_settings", lambda: DummySettings(enable_pr_type=True, generate_ai_title=True, enable_semantic_files_types=True, file_table_collapsible_open_by_default=False))
    yield


def _make_pr_instance():
    # Create instance without running __init__ (to avoid external dependencies)
    pr = PRDescription.__new__(PRDescription)
    # Minimal attributes used by _prepare_pr_answer
    pr.vars = {"title": "Original Title"}
    pr.file_label_dict = []
    # default git provider (tests will set appropriate supported features)
    pr.git_provider = DummyGitProvider()
    return pr


def test_prepare_pr_answer_generate_title_round_017(monkeypatch):
    """Covers branches when labels are removed, AI title used, diagram and walkthrough rendering,
    semantic file table branch and open-by-default collapsible behavior.
    """
    # Prepare PRDescription instance
    pr = _make_pr_instance()

    # Data contains a 'labels' key that should be removed when git provider supports get_labels
    # 'title' should be popped and used (generate_ai_title True)
    # 'changes_diagram' should render DIAGRAM_WALKTHROUGH
    # 'file_walkthrough' contains walkthrough files to trigger gfm_markdown details
    # 'pr_files' will trigger process_pr_files_prediction (semantic files enabled)
    pr.data = OrderedDict([
        ("labels", ["label1"]),
        ("title", "AI Generated Title"),
        ("changes_diagram", "diagram: ascii"),
        ("file_walkthrough", [{"filename": "a.py", "changes_in_file": "changed lines"}]),
        ("pr_files", None),
        ("description", "one\n-two"),
    ])

    pr.vars = {"title": "Original Title"}
    pr.file_label_dict = [{"filename": "z.txt", "changes_in_file": "z changed"}]

    # Make git provider support both get_labels and gfm_markdown
    pr.git_provider = DummyGitProvider(supported=("get_labels", "gfm_markdown"))

    # Monkeypatch process_pr_files_prediction to avoid heavy logic and return known table + changes
    expected_table = "<table><tr><td>file</td></tr></table>"
    expected_pr_file_changes = [{"filename": "z.txt", "changes_in_file": "z changed"}]

    monkeypatch.setattr(PRDescription, "process_pr_files_prediction", lambda self, cw, v: (expected_table, expected_pr_file_changes))

    # Make settings: enable_semantic_files_types True and file_table_collapsible_open_by_default True
    import pr_agent.tools.pr_description as mod
    monkeypatch.setattr(mod, "get_settings", lambda: DummySettings(enable_pr_type=True, generate_ai_title=True, enable_semantic_files_types=True, file_table_collapsible_open_by_default=True))

    # Call the method under test
    title, pr_body, changes_walkthrough, pr_file_changes = pr._prepare_pr_answer()

    # Oracle assertions
    # Title should be the AI-generated title (ai_title popped from data)
    assert title == "AI Generated Title"

    # 'labels' key must have been removed from the original data structure
    assert "labels" not in pr.data

    # Diagram header should be present (value from PRDescriptionHeader enum)
    assert PRDescriptionHeader.DIAGRAM_WALKTHROUGH.value in pr_body
    # Diagram content should be present
    assert "diagram: ascii" in pr_body

    # Walkthrough files from 'file_walkthrough' should render using gfm_markdown-style details (summary present)
    assert "<details> <summary>files:</summary>" in pr_body
    # The specific file entry from file_walkthrough should appear formatted inline
    assert "`a.py`" in pr_body and "changed lines" in pr_body

    # The semantic files table returned by process_pr_files_prediction should be exposed in changes_walkthrough
    assert expected_table in changes_walkthrough
    # And the returned pr_file_changes should be forwarded unchanged
    assert pr_file_changes == expected_pr_file_changes
    assert pr_file_changes[0]["filename"] == "z.txt"


def test_prepare_pr_answer_no_generate_title_round_017(monkeypatch):
    """Covers branches where AI title is not used (generate_ai_title False),
    'type' key must be printed as 'PR Type', description list handling, and
    the non-semantic pr_files handling (enable_semantic_files_types False) with separators.
    """
    pr = _make_pr_instance()

    # Data contains 'type' (to exercise Type -> PR Type mapping), 'title' present but should not be used,
    # 'pr_files' will be present but semantic files disabled so fallback path is used,
    # description as a list should be joined and have newline hyphen replacement applied
    pr.data = OrderedDict([
        ("title", "AI Title Not Used"),
        ("type", "bug"),
        ("pr_files", None),
        ("description", ["first\n-second", "extra"]),
    ])

    pr.vars = {"title": "Original Title"}
    # When semantic files are disabled, pr.file_label_dict should be a list of strings so fallback join works
    pr.file_label_dict = ["fileA", "fileB"]

    # Git provider does not need gfm_markdown here; ensure get_labels not supported so labels branch not triggered
    pr.git_provider = DummyGitProvider(supported=())

    # Patch settings: do not generate AI title, enable_pr_type True, disable semantic files
    import pr_agent.tools.pr_description as mod
    monkeypatch.setattr(mod, "get_settings", lambda: DummySettings(enable_pr_type=True, generate_ai_title=False, enable_semantic_files_types=False, file_table_collapsible_open_by_default=False))

    # Call the method under test
    title, pr_body, changes_walkthrough, pr_file_changes = pr._prepare_pr_answer()

    # Oracle assertions
    # Since generate_ai_title is False, original vars title should be returned
    assert title == "Original Title"

    # 'Type' header should be replaced by 'PR Type' as per code path
    assert "PR Type" in pr_body
    assert "bug" in pr_body

    # pr_files fallback should join file_label_dict values into the body when semantic files disabled
    assert "fileA, fileB" in pr_body

    # Description list should be joined and the '\n-' -> '\n\n-' replacement applied
    assert "first\n\n-" in pr_body  # replacement adds an extra newline before '-' per code
    assert "extra" in pr_body

    # Because there are multiple items, separators '___' should be present between sections
    assert "___" in pr_body

    # When semantic is disabled, we expect no changes_walkthrough table generated
    assert changes_walkthrough == ""
    assert pr_file_changes == []
