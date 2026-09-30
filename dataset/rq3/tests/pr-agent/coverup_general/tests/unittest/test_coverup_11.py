# file: pr_agent/tools/pr_description.py:548-622
# asked: {"lines": [559, 560, 561, 562, 565, 566, 568, 571, 575, 576, 577, 578, 579, 580, 581, 582, 583, 585, 586, 587, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 605, 606, 607, 608, 609, 610, 611, 612, 613, 616, 617, 618, 619, 620, 622], "branches": [[559, 560], [559, 561], [561, 562], [561, 565], [566, 568], [566, 571], [577, 578], [577, 622], [578, 579], [578, 582], [582, 583], [582, 585], [586, 587], [586, 590], [591, 592], [591, 600], [592, 593], [592, 594], [594, 595], [594, 598], [598, 599], [598, 619], [600, 601], [600, 609], [602, 603], [602, 605], [609, 610], [609, 616], [610, 611], [610, 612], [616, 617], [616, 618], [619, 577], [619, 620]]}
# gained: {"lines": [559, 560, 561, 562, 565, 566, 568, 571, 575, 576, 577, 578, 579, 580, 581, 582, 583, 585, 586, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 606, 607, 608, 609, 610, 611, 612, 613, 616, 618, 619, 620, 622], "branches": [[559, 560], [559, 561], [561, 562], [561, 565], [566, 568], [566, 571], [577, 578], [577, 622], [578, 579], [578, 582], [582, 583], [582, 585], [586, 590], [591, 592], [591, 600], [592, 593], [594, 595], [594, 598], [598, 599], [600, 601], [600, 609], [602, 603], [609, 610], [609, 616], [610, 611], [616, 618], [619, 577], [619, 620]]}

import types
from types import SimpleNamespace
from collections import OrderedDict

import pytest

from pr_agent.tools.pr_description import PRDescription
from pr_agent.algo.utils import PRDescriptionHeader


class DummyGitProvider:
    def __init__(self, supported=None):
        self.supported = supported or set()

    def is_supported(self, feature):
        return feature in self.supported


class SettingsStub:
    def __init__(self, pr_description_dict):
        # pr_description should behave like an object with attributes and a .get method
        self.pr_description = SimpleNamespace(**pr_description_dict)
        def get(key, default=None):
            return pr_description_dict.get(key, default)
        self.pr_description.get = get


def make_prdescription_instance():
    inst = PRDescription.__new__(PRDescription)
    return inst


def test_prepare_pr_answer_labels_type_and_generate_ai_title_false(monkeypatch):
    settings = SettingsStub({
        "enable_pr_type": False,
        "generate_ai_title": False,
        "enable_semantic_files_types": False,
        "file_table_collapsible_open_by_default": False,
    })
    # Monkeypatch the get_settings used inside pr_agent.tools.pr_description
    monkeypatch.setattr("pr_agent.tools.pr_description.get_settings", lambda: settings)

    inst = make_prdescription_instance()
    inst.data = OrderedDict([
        ("labels", ["L1"]),
        ("type", "bug"),
        ("title", "AI Generated Title"),
        ("description", ["first line", "second line-"]),
        ("extra", "some extra info"),
    ])
    inst.vars = {"title": "Original Title"}
    inst.file_label_dict = {}
    inst.git_provider = DummyGitProvider(supported={"get_labels"})

    title, pr_body, changes_walkthrough, pr_file_changes = inst._prepare_pr_answer()

    assert title == "Original Title"
    assert "labels" not in inst.data
    assert "type" not in inst.data
    # Description header and content present
    assert "### **Description**" in pr_body
    assert "first line" in pr_body and "second line-" in pr_body
    # Extra section present with header and content
    assert "### **Extra**" in pr_body and "some extra info" in pr_body
    # Separator should be present because multiple entries
    assert "___" in pr_body
    assert changes_walkthrough == ""
    assert pr_file_changes == []


def test_prepare_pr_answer_diagram_pr_files_and_walkthrough_with_gfm_and_collapsible_open(monkeypatch):
    settings = SettingsStub({
        "enable_pr_type": True,
        "generate_ai_title": True,
        "enable_semantic_files_types": True,
        "file_table_collapsible_open_by_default": True,
    })
    monkeypatch.setattr("pr_agent.tools.pr_description.get_settings", lambda: settings)

    inst = make_prdescription_instance()
    inst.vars = {"title": "Original Title"}
    inst.data = OrderedDict([
        ("title", "AI Title Here"),
        ("changes_diagram", "diagram: ascii-art"),
        ("file_walkthrough", [
            {"filename": "some'file.py", "changes_in_file": "changed X"},
            {"filename": "another.py", "changes_in_file": "changed Y"},
        ]),
        ("pr_files", [{"dummy": "value"}]),
    ])
    inst.file_label_dict = [{"filename": "should_not_be_used.py", "changes_in_file": "n/a"}]
    inst.git_provider = DummyGitProvider(supported={"gfm_markdown"})
    called = {}

    def fake_process(changes_walkthrough, value):
        called['in_changes_walkthrough'] = changes_walkthrough
        called['in_value'] = value
        return ("|file|table|", [{"filename": "a.py", "type": "modified"}])

    inst.process_pr_files_prediction = fake_process

    title, pr_body, changes_walkthrough, pr_file_changes = inst._prepare_pr_answer()

    assert title == "AI Title Here"
    assert PRDescriptionHeader.DIAGRAM_WALKTHROUGH.value in pr_body
    assert "diagram: ascii-art" in pr_body
    # The walkthrough details should be present for file_walkthrough (gfm_markdown supported)
    assert "<details" in pr_body and "files:" in pr_body
    # The filename apostrophe should have been replaced by a backtick sequence inside the body string
    assert "some`file.py" in pr_body
    # process_pr_files_prediction should have been called with file_label_dict
    assert called['in_value'] == inst.file_label_dict
    # changes_walkthrough should include the returned table and be in an open details
    assert "|file|table|" in changes_walkthrough
    assert "<details open>" in changes_walkthrough or "<details open" in changes_walkthrough
    assert pr_file_changes == [{"filename": "a.py", "type": "modified"}]
