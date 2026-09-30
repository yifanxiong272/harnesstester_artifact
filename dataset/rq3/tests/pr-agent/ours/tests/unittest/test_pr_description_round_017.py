import types
import builtins
import pytest

from pr_agent.tools import pr_description as pd_mod
from pr_agent.tools.pr_description import PRDescription


class _FakePDSettings:
    def __init__(self, enable_pr_type=True, generate_ai_title=True, enable_semantic_files_types=False, file_table_collapsible_open_by_default=False):
        self.enable_pr_type = enable_pr_type
        self.generate_ai_title = generate_ai_title
        self.enable_semantic_files_types = enable_semantic_files_types
        # provide dict-like .get used by code
        self._extra = {"file_table_collapsible_open_by_default": file_table_collapsible_open_by_default}

    def get(self, key, default=None):
        return self._extra.get(key, default)


class _FakeSettings:
    def __init__(self, pd: _FakePDSettings):
        self.pr_description = pd


class _GP:
    def __init__(self, supported=None):
        # supported: set/list of features to return True for
        self._supported = set(supported or [])

    def is_supported(self, name: str) -> bool:
        return name in self._supported


def _make_instance():
    # Create PRDescription instance without running its real __init__
    inst = object.__new__(PRDescription)
    return inst


def test_labels_and_ai_title_generation_round_017(monkeypatch):
    """Exercise: labels removal, title selection when generate_ai_title is False, and 'description' handling."""
    # Arrange
    inst = _make_instance()
    inst.vars = {"title": "ORIGINAL_TITLE"}
    # include 'labels' to be removed when provider supports get_labels
    inst.data = {
        "labels": ["L1"],
        "title": "AI_PROPOSED_TITLE",
        "description": ["first line\n- bullet item"]
    }
    inst.file_label_dict = {}
    inst.process_pr_files_prediction = lambda cw, v: ("", [])
    inst.git_provider = _GP(supported=["get_labels"])  # supports label removal

    # Patch settings: enable_pr_type True (so 'type' not popped) and generate_ai_title False
    fake_pd = _FakePDSettings(enable_pr_type=True, generate_ai_title=False)
    monkeypatch.setattr(pd_mod, "get_settings", lambda: _FakeSettings(fake_pd))

    # Act
    title, pr_body, changes_walkthrough, pr_file_changes = pd_mod.PRDescription._prepare_pr_answer(inst)

    # Assert
    # labels should be removed from the original data before iteration
    assert "labels" not in inst.data
    # title should be taken from vars because generate_ai_title is False
    assert title == "ORIGINAL_TITLE"
    # the description list should be joined and bullets reformatted
    assert "first line" in pr_body
    # the function replaces "\n-" with "\n\n-" so the bullet should be separated
    assert "\n\n- bullet item" in pr_body
    # When only 'description' remains there should be no changes_walkthrough or file changes
    assert changes_walkthrough == ""
    assert pr_file_changes == []


def test_walkthrough_and_pr_files_round_017(monkeypatch):
    """Exercise: changes_diagram, walkthrough with gfm_markdown details, and pr_files semantic branch producing collapsible details."""
    inst = _make_instance()
    inst.vars = {"title": "ORIG"}

    # include multiple keys to drive several branches in the loop order
    # 1) changes_diagram should add the DIAGRAM header and the diagram text
    # 2) files_walkthrough (contains 'walkthrough' substring) should produce a details section
    # 3) pr_files should be replaced by file_label_dict and processed by process_pr_files_prediction
    diagram_text = "graph LR; A-->B"

    # files_walkthrough value is a list of file dicts for the walkthrough branch
    walkthrough_files = [{"filename": "a'b.py", "changes_in_file": "did change"}]

    inst.data = {
        "changes_diagram": diagram_text,
        "files_walkthrough": walkthrough_files,
        "pr_files": [  # will be ignored and replaced by inst.file_label_dict
            {"will": "be replaced"}
        ],
        "other": "value"
    }

    # file_label_dict is used when key == 'pr_files'
    inst.file_label_dict = [
        {"filename": "file1.py", "changes_in_file": "x"}
    ]

    # patch process_pr_files_prediction to return a fake table and list of file changes
    def fake_process(cw, value):
        # ensure we receive the inst.file_label_dict as value
        assert value == inst.file_label_dict
        return ("<table>content</table>", [{"fname": "file1.py"}])

    inst.process_pr_files_prediction = fake_process

    # git provider supports gfm_markdown so walkthrough will wrap with details tags
    inst.git_provider = _GP(supported=["gfm_markdown"])

    # Patch settings to enable semantic files types and make the file table collapsible open by default
    fake_pd = _FakePDSettings(enable_pr_type=True, generate_ai_title=True, enable_semantic_files_types=True, file_table_collapsible_open_by_default=True)
    monkeypatch.setattr(pd_mod, "get_settings", lambda: _FakeSettings(fake_pd))

    # Act
    title, pr_body, changes_walkthrough, pr_file_changes = pd_mod.PRDescription._prepare_pr_answer(inst)

    # Assert
    # title should be taken from data's title fallback (ai_title path): since no 'title' in data now (we didn't include 'title'), ai_title uses vars
    assert title == "ORIG"

    # changes_diagram branch should add the diagram header and the diagram itself
    assert pd_mod.PRDescriptionHeader.DIAGRAM_WALKTHROUGH.value in pr_body
    assert diagram_text in pr_body

    # files_walkthrough branch should include a details opening and closing (because gfm_markdown supported)
    assert "<details>" in pr_body or "</details>" in pr_body

    # single-quote in filename should be replaced with backtick inside the generated line
    # original filename: "a'b.py" -> becomes "a`b.py" in the markdown code span
    assert "a`b.py" in pr_body
    assert "did change" in pr_body

    # pr_files branch should cause process_pr_files_prediction to be called and changes_walkthrough to include the returned table
    assert "<table>content</table>" in changes_walkthrough
    # because file_table_collapsible_open_by_default True we expect the details tag to include ' open'
    assert "<details open>" in changes_walkthrough
    # pr_file_changes should be the list returned by fake_process
    assert pr_file_changes == [{"fname": "file1.py"}]


# Ensure test discovery picks up the module name and both tests
